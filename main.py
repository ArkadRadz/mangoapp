from flask import render_template, request, jsonify
from flask.helpers import url_for
from flask_session import Session
from werkzeug.utils import redirect
from setup import app, db
from mangatag import Manga, Tag
from author import Author
from image import Image
from manga_scanner import scan_dir_for_mangas
from flask_caching import Cache
import re

app.secret_key = "super secret key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
cache = Cache(app)


@app.route("/")
def home():
    recent_mangas = db.session.query(Manga).order_by(Manga.id.desc()).limit(3).all()
    return render_template("main.html", mangas=recent_mangas)


def mangas_to_set(recent_mangas, generate_thumbnail=True, only_first_image=False):
    result = []

    for recent_manga in recent_mangas:
        recent_manga_author = db.session.query(Author).get(recent_manga.author_id)
        base_image_path = recent_manga.dir_name + "/"
        images = []

        if only_first_image is False:
            for image in recent_manga.images:
                if generate_thumbnail is True:
                    image_path = (
                        "thumbnails/"
                        + base_image_path
                        + "/"
                        + convert_to_thumbnail(image.path)
                    )
                else:
                    image_path = base_image_path + image.path

                images.append(image_path)
        else:
            base_image_url = recent_manga.images[0].path

            if generate_thumbnail is True:
                images = (
                    "thumbnails/"
                    + base_image_path
                    + "/"
                    + convert_to_thumbnail(base_image_url)
                )
            else:
                images = base_image_path + base_image_url

        result.append(
            {
                "title": recent_manga.title,
                "author": recent_manga_author.name,
                "images": images,
            }
        )

    return result


@app.route("/api/recent-mangas")
def recent_mangas_api():
    recent_mangas = db.session.query(Manga).order_by(Manga.id.desc()).limit(3).all()

    result = mangas_to_set(recent_mangas)

    return jsonify(result)


@app.route("/api/mangas", defaults={"current_page": 1})
@app.route("/api/mangas/<int:current_page>")
def api_mangas(current_page):
    manga_query = (
        db.session.query(Manga)
        .order_by(Manga.id)
        .paginate(page=current_page, per_page=9)
    )

    return jsonify(mangas_to_set(manga_query.items))


@app.route("/api/manga/<int:id>", defaults={"current_page": 1})
@app.route("/api/manga/<int:id>/<int:current_page>")
def api_manga_overview(id, current_page):
    manga = db.session.query(Manga).get(id)
    manga_images = (
        db.session.query(Image)
        .filter_by(manga_id=manga.id)
        .paginate(page=current_page, per_page=30)
    )

    author = db.session.query(Author).get(manga.author_id)

    manga_image_set = []

    for image in manga_images.items:
        manga_image_set.append(image.path)

    manga = db.session.query(Manga).get(id)

    data = {
        "manga": {"title": manga.title},
        "author": {"id": author.id, "name": author.name},
        "images": manga_image_set,
    }

    return jsonify(data)


def authors_to_set(authors):
    authors_data = []

    for author in authors:
        mangas = mangas_to_set(author.manga, only_first_image=True)

        data = {"author_name": author.name, "mangas": mangas}

        authors_data.append(data)

    return authors_data


@app.route("/api/authors", defaults={"current_page": 1})
@app.route("/api/authors/<int:current_page>")
def api_authors(current_page):
    author_query = (
        db.session.query(Author)
        .order_by(Author.id)
        .paginate(page=current_page, per_page=25)
    )

    return jsonify(authors_to_set(author_query.items))


@app.route("/api/author/<int:id>", defaults={"current_page": 1}, strict_slashes=False)
@app.route("/api/author/<int:id>/<int:current_page>")
def api_author_overview(id, current_page):
    author = db.session.query(Author).get(id)
    author_mangas = (
        db.session.query(Manga)
        .filter_by(author_id=author.id)
        .paginate(page=current_page, per_page=9)
    )

    mangas = []

    for manga in author_mangas.items:
        base_image_path = manga.dir_name + "/"
        length = len(manga.images)
        thumbnail = (
            "thumbnails/"
            + base_image_path
            + "/"
            + convert_to_thumbnail(manga.images[0].path)
        )

        mangas.append(
            {
                "id": manga.id,
                "title": manga.title,
                "length": length,
                "thumbnail": thumbnail,
            }
        )

    return jsonify(
        {
            "author": author.name,
            "mangas": mangas,
            "manga_pages": author_mangas.pages,
        }
    )


@app.route(
    "/api/manga/read/<int:manga_id>", defaults={"page_number": 1}, strict_slashes=False
)
@app.route("/api/manga/read/<int:manga_id>/<int:page_number>")
def api_manga_page(manga_id, page_number):
    manga_result = db.session.query(Manga).get(manga_id)
    image = manga_result.images[page_number - 1]
    manga_images = (
        db.session.query(Image)
        .filter_by(manga_id=manga_result.id)
        .paginate(page=page_number, per_page=1)
    )

    data = {
        "manga_id": manga_id,
    }

    if manga_images.has_next:
        image = manga_result.images[manga_images.next_num]
        image_path = "mangas" + "/" + manga_result.dir_name + "/" + image.path
        data["next_image"] = {
            "id": manga_images.next_num,
            "url": image_path,
        }

    if manga_images.has_prev:
        image = manga_result.images[manga_images.prev_num]
        image_path = "mangas" + "/" + manga_result.dir_name + "/" + image.path
        data["prev_image"] = {
            "id": manga_images.prev_num,
            "url": image_path,
        }

    return jsonify(data)


@app.route("/api/search")
def api_search():
    mangas = None

    query = request.args.get("query")
    current_page = request.args.get("page")

    results = []

    if current_page is None:
        current_page = 1
    else:
        current_page = int(current_page)

    if query is not None:
        tags_regex_search = re.findall(r"\w+|'.*'|\w+", query)

        if tags_regex_search:
            print(current_page)
            search_tags = [tag.replace("'", "") for tag in tags_regex_search]
            mangas = (
                db.session.query(Manga)
                .join(Tag.mangas)
                .filter(
                    Tag.value.in_(search_tags) | Manga.title.like("%" + query + "%")
                )
                .paginate(page=current_page, per_page=9)
            )
        else:
            mangas = (
                db.session.query(Manga)
                .filter(Manga.title.like("%" + query + "%"))
                .paginate(page=current_page, per_page=9)
            )

        return jsonify(
            {
                "results": mangas_to_set(mangas.items, True, True),
                "pages": mangas.pages,
            }
        )

    return "No query provided"


@app.route("/search")
def search():
    mangas = None

    query = request.args.get("query")
    current_page = request.args.get("page")

    results = []

    if current_page is None:
        current_page = 1
    else:
        current_page = int(current_page)

    if query is not None:
        tags_regex_search = re.findall(r"\w+|'.*'|\w+", query)

        if tags_regex_search:
            print(current_page)
            search_tags = [tag.replace("'", "") for tag in tags_regex_search]
            mangas = (
                db.session.query(Manga)
                .join(Tag.mangas)
                .filter(
                    Tag.value.in_(search_tags) | Manga.title.like("%" + query + "%")
                )
                .paginate(page=current_page, per_page=9)
            )
        else:
            mangas = (
                db.session.query(Manga)
                .filter(Manga.title.like("%" + query + "%"))
                .paginate(page=current_page, per_page=9)
            )

    return render_template("search.html", mangas=mangas, query=query)


@app.route("/clear-cache")
def clear_cache():
    cache.init_app(app, config=app.config)

    with app.app_context():
        cache.clear()


@app.route("/mangas", defaults={"current_page": 1})
@app.route("/mangas/<int:current_page>")
def mangas(current_page):
    manga_query = (
        db.session.query(Manga)
        .order_by(Manga.id)
        .paginate(page=current_page, per_page=9)
    )

    return render_template("mangas.html", mangas=manga_query)


@app.route("/manga/<int:id>", defaults={"current_page": 1})
@app.route("/manga/<int:id>/<int:current_page>")
def manga_overview(id, current_page):
    manga = db.session.query(Manga).get(id)
    manga_images = (
        db.session.query(Image)
        .filter_by(manga_id=manga.id)
        .paginate(page=current_page, per_page=30)
    )
    manga_author = db.session.query(Author).get(manga.author_id)

    return render_template(
        "manga_overview.html",
        manga=manga,
        manga_images=manga_images,
        manga_author=manga_author,
    )


@app.route(
    "/manga/read/<int:manga_id>", defaults={"page_number": 1}, strict_slashes=False
)
@app.route("/manga/read/<int:manga_id>/<int:page_number>")
def manga_page(manga_id, page_number):
    manga_result = db.session.query(Manga).get(manga_id)
    image = manga_result.images[page_number - 1]
    manga_images = (
        db.session.query(Image)
        .filter_by(manga_id=manga_result.id)
        .paginate(page=page_number, per_page=1)
    )

    return render_template(
        "manga_page.html", manga=manga_result, image=image, manga_images=manga_images
    )


@app.route("/authors", defaults={"current_page": 1})
@app.route("/authors/<int:current_page>")
def authors(current_page):
    author_query = (
        db.session.query(Author)
        .order_by(Author.id)
        .paginate(page=current_page, per_page=25)
    )

    return render_template("authors.html", authors=author_query)


@app.route("/author/<int:id>", defaults={"current_page": 1}, strict_slashes=False)
@app.route("/author/<int:id>/<int:current_page>")
def author_overview(id, current_page):
    author = db.session.query(Author).get(id)
    author_mangas = (
        db.session.query(Manga)
        .filter_by(author_id=author.id)
        .paginate(page=current_page, per_page=9)
    )

    return render_template("author_overview.html", author=author, mangas=author_mangas)


@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/handle_data", methods=["POST"])
def handle_data():
    dir_path = request.form["dirpath"]
    print(f"Attempting to scan {dir_path} for mangas")
    count = scan_dir_for_mangas(dir_path, app.root_path)

    return redirect(url_for("scan"))


@app.template_filter()
def convert_to_thumbnail(image_name):
    if ".png" in image_name:
        return image_name.replace(".png", "-t.png")
    elif ".jpeg" in image_name:
        return image_name.replace(".jpeg", "-t.jpeg")
    elif ".jpg" in image_name:
        return image_name.replace(".jpg", "-t.jpg")

    return image_name


if __name__ == "__main__":
    sess = Session()
    sess.init_app(app)
    app.run(debug=True, host="0.0.0.0", port="9876")
