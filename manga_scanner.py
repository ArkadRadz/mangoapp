from setup import *
import os
import re
from flask.helpers import flash
from tqdm import tqdm
from author import Author
from manga import Manga
from image import Image
from thumbnail_maker import create_thumbnail_for_image

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
            flash(f"I couldn't process directory: {element.path}")
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
                create_thumbnail_for_image(sub_element)

        author.manga.append(manga)
        db.session.add_all([author, manga])
        db.session.commit()

    return mangas