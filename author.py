from setup import *

class Author(db.Model):
    __tablename__ = "author"
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String, unique=True)
    manga = db.relationship('Manga')