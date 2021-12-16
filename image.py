from setup import *

class Image(db.Model):
    __tablename__ = "image"
    id = db.Column('id', db.Integer, primary_key=True)
    path = db.Column('path', db.String, unique=False)
    manga_id = db.Column(db.Integer, db.ForeignKey('manga.id'))