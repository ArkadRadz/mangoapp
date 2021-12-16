import os
from flask.helpers import flash
from PIL import Image
import pathlib
import sys

from flask.json.tag import TaggedJSONSerializer

def scan_dir_for_mangas(dir_path = None):
    mangas = []

    try:
        with os.scandir(dir_path) as elements:
            for element in elements:
                try:
                    sub_elements = os.scandir(element.path)
                except FileNotFoundError:
                    print("Something went wrong. Received file not found error.")
                    continue

                for sub_element in sub_elements:
                    if sub_element.is_file:
                        create_thumbnail_for_image(sub_element)

    except FileNotFoundError:
        flash(f"Unknown path {dir_path}")
        return mangas

def create_thumbnail_for_image(sub_element):
    target_path = sub_element.path.replace(sub_element.name, '')

    if '-t.' in sub_element.path:
        return

    if '.png' in sub_element.name:
        image_thumbnail_name = sub_element.name.replace('.png', '-t.png')
    elif '.jpeg' in sub_element.name:
        image_thumbnail_name = sub_element.name.replace('.jpeg', '-t.jpeg')
    elif '.jpg' in sub_element.name:
        image_thumbnail_name = sub_element.name.replace('.jpg', '-t.jpg')

    image = Image.open(sub_element.path)
    image_size = image.size
    image.thumbnail((image_size[0] * 0.25, image_size[1] * 0.25))

    static_path = target_path.rsplit(os.sep)[:-3]
    manga_name = target_path.rsplit(os.sep)[-2]
    static_path.append('thumbnails')

    thumbnail_path = os.sep.join(static_path)
    thumbnail_path += os.sep + manga_name + os.sep

    if not os.path.exists(thumbnail_path):
        os.makedirs(thumbnail_path)

    image_path = thumbnail_path + image_thumbnail_name

    if os.path.isfile(image_path):
        return

    image.save(image_path)