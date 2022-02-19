from metadata_scanner import Scanner
from setup import *
import os
import re
from flask.helpers import flash
from tqdm import tqdm
from author import Author
from mangatag import Manga
from image import Image
from thumbnail_maker import create_thumbnail_for_image

def scan_dir_for_mangas(dir_path = None, root_path = None):
    db.create_all()

    mangas = []

    try:
        elements = os.scandir(dir_path)
    except FileNotFoundError:
        flash(f"Unknown path {dir_path}")
        return mangas
    thumbnail_path = root_path + os.sep + 'static' + os.sep + 'thumbnails'

    total_count = os.listdir(dir_path).__len__()
    tqdm_elements = tqdm(elements, total=total_count)
    for element in tqdm_elements:
        with db.session.no_autoflush:
            tqdm_elements.set_postfix({'current_element': element.name})
            try:
                sub_elements = os.scandir(element.path)
            except FileNotFoundError:
                flash(f"I couldn't process directory: {element.path}")
                continue

            manga = create_manga(root_path, element, sub_elements) 

            author = create_author(element, manga)

            author.manga.append(manga)

            db.session.add(author)
        db.session.commit()

    return mangas

def create_author(element, manga):
    regex_author = re.search("\[(.*?)\]", element.name)

    if regex_author is not None:
        author_name = (regex_author.group(0))[1:-1]
    else:
        author_name = 'Unknown'

    author = db.session.query(Author).filter(Author.name.contains(author_name)).first()
    
    if author == None:
        author = Author()
        author.name = author_name

    return author

def create_manga(root_path, element, sub_elements):
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
    else:
        return manga

    code_search = re.search(r'^\d*', element.name)

    if code_search and code_search.group() != '':
        code = code_search.group()
    else:
        code = element.name

    metadata_scanners = Scanner.__subclasses__

    tags = []

    for scanner in metadata_scanners:
        tags.append(scanner.scan(code))

    for sub_element in sub_elements:
        if sub_element.is_file:
            image = Image()
            image.path = sub_element.name

            manga.images.append(image)
            create_thumbnail_for_image(sub_element, root_path)

    tags = set(tags)

    for tag in tags:
        tag_db = db.session.query(Tag).filter(Tag.value == tag.value).first()
        if tag_db is not None:
            tag = tag_db
        else:
            db.session.add(tag)

        print(f'{tag.value} - {tag.type}')

        manga.tags.append(tag)

    return manga

# scan_dir_for_mangas(r'C:\Users\Arek\Python\Mangas\static\mangas', r'C:\Users\Arek\Python\Mangas')