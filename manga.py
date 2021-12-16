from setup import *

class Manga(db.Model):
    __tablename__ = "manga"
    id = db.Column('id', db.Integer, primary_key=True)
    title = db.Column('title', db.String, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    dir_name = db.Column('dir_name', db.String)
    images = db.relationship('Image')