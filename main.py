from flask import render_template, request, session
from flask.helpers import url_for
from flask_session import Session
from tqdm import tqdm
from werkzeug.utils import redirect
from setup import *
from manga import Manga
from author import Author
from image import Image
from manga_scanner import scan_dir_for_mangas

# scan_dir_for_mangas()

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/mangas', defaults={'current_page': 1})
@app.route('/mangas/<int:current_page>')
def mangas(current_page):
    manga_query = db.session.query(Manga).order_by(Manga.id).paginate(page=current_page, per_page=9)

    return render_template('mangas.html', mangas=manga_query)

@app.route('/authors', defaults={'current_page': 1})
@app.route('/authors/<int:current_page>')
def authors(current_page):
    author_query = db.session.query(Author).order_by(Author.id).paginate(page=current_page, per_page=10)

    return render_template('authors.html', authors=author_query)

@app.route('/author/<int:id>')
def author_overview(id):
    author = db.session.query(Author).get(id)
    author_mangas = db.session.query(Manga).filter_by(author_id=author.id)

    return render_template('author_overview.html', author=author, mangas=author_mangas)

@app.route('/manga/<int:id>')
def manga_overview(id):
    manga = db.session.query(Manga).get(id)
    manga_images  = db.session.query(Image).filter_by(manga_id=manga.id)
    manga_author = db.session.query(Author).get(manga.author_id)

    return render_template('manga_overview.html', manga=manga, manga_images=manga_images, manga_author=manga_author)

@app.route('/manga/<int:manga_id>/<int:page_number>')
def manga_page(manga_id, page_number):
    manga_result = db.session.query(Manga).get(manga_id)
    image = manga_result.images[page_number - 1]
    manga_images  = db.session.query(Image).filter_by(manga_id=manga_result.id).paginate(page=page_number, per_page=1)

    return render_template('manga_page.html', manga=manga_result, image=image, manga_images=manga_images)

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/handle_data', methods=['POST'])
def handle_data():
    dir_path = request.form['dirpath']
    print(f"Attempting to scan {dir_path} for mangas")
    count = scan_dir_for_mangas(dir_path)

    return redirect(url_for('scan'))

if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    sess = Session()
    sess.init_app(app)
    app.run(debug=True, host="0.0.0.0", port="9876")