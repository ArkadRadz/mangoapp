import os
import re
from flask import Flask, render_template, request, session
from flask.helpers import flash, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from tqdm import tqdm
from werkzeug.utils import redirect, send_from_directory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///manga.db'
db = SQLAlchemy(app)

class Manga(db.Model):
    __tablename__ = "manga"
    id = db.Column('id', db.Integer, primary_key=True)
    title = db.Column('title', db.String, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    dir_name = db.Column('dir_name', db.String)
    images = db.relationship('Image')


class Image(db.Model):
    __tablename__ = "image"
    id = db.Column('id', db.Integer, primary_key=True)
    path = db.Column('path', db.String, unique=False)
    manga_id = db.Column(db.Integer, db.ForeignKey('manga.id'))


class Author(db.Model):
    __tablename__ = "author"
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String, unique=True)
    manga = db.relationship('Manga')

def scan_dir_for_mangas(dir_path = None):
    db.create_all()

    mangas = []

    try:
        elements = os.scandir(dir_path)
    except FileNotFoundError:
        flash(f"Unknown path {dir_path}")
        return mangas

    total_count = os.listdir(dir_path).__len__()
    tqdm_elements = tqdm(elements, total=total_count)
    for element in tqdm_elements:
        tqdm_elements.set_postfix({'current_element': element.name})
        try:
            sub_elements = os.scandir(element.path)
        except FileNotFoundError:
            print(f"I couldn't process directory: {element.path}")
            continue

        regex_author = re.search("\[(.*?)\]", element.name)

        if regex_author is not None:
            author_name = (regex_author.group(0))[1:-1]
        else:
            author_name = 'Unknown'

        author = db.session.query(Author).filter(Author.name.contains(author_name)).first()
        if author == None:
            print(f"Created author {author_name}")
            author = Author()
            author.name = author_name

        regex_manga = re.search("\](.*?)\[", element.name)

        if regex_manga is not None:
            manga_title = (regex_manga.group(0))[1:-1]
        else:
            manga_title = element.name

        manga = db.session.query(Manga).filter(Manga.title.contains(manga_title)).first()

        if manga == None:
            manga = Manga()
            manga.title = manga_title
            manga.dir_name = element.name
            print(f"Created manga {manga.title}")
        else:
            continue

        for sub_element in sub_elements:
            if sub_element.is_file:
                image = Image()
                image.path = sub_element.name

                manga.images.append(image)

        author.manga.append(manga)
        db.session.add_all([author, manga])
        db.session.commit()

    return mangas

# scan_dir_for_mangas()

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/mangas')
def mangas():
    manga_query = db.session.query(Manga).order_by(Manga.id).paginate(per_page=9)

    return render_template('mangas.html', mangas=manga_query)

@app.route('/authors')
def authors():
    author_query = db.session.query(Author).order_by(Author.id).paginate(per_page=10)
    return render_template('authors.html', authors=author_query)

@app.route('/author/<id>')
def author_overview(id):
    author = db.session.query(Author).get(id)
    author_mangas = db.session.query(Manga).filter_by(author_id=author.id)
    return render_template('author_overview.html', author=author, mangas=author_mangas)

@app.route('/manga/<id>')
def manga_overview(id):
    manga = db.session.query(Manga).get(id)
    manga_images  = db.session.query(Image).filter_by(manga_id=manga.id)
    manga_author = db.session.query(Author).get(manga.author_id)
    pages = manga_images.count()
    return render_template('manga_overview.html', manga=manga, manga_images=manga_images, manga_author=manga_author, pages=pages)

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