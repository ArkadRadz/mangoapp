from setup import *

class MangaTag(db.Model):
    __tablename__ = "manga_tag"
    id = db.Column('id', db.Integer, primary_key=True)
    manga_id = db.Column('mangaId', db.Integer, db.ForeignKey('manga.id'))
    tag_id = db.Column('tagId', db.Integer, db.ForeignKey('tag.id'))

class Manga(db.Model):
    __tablename__ = "manga"
    id = db.Column('id', db.Integer, primary_key=True)
    title = db.Column('title', db.String, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    dir_name = db.Column('dir_name', db.String)
    images = db.relationship('Image')

class Tag(db.Model):
    TYPE_CHARACTER = 'character'
    TYPE_GROUP = 'group'
    TYPE_PARODY = 'parody'
    TYPE_TAG = 'tag'

    __tablename__ = "tag"
    id = db.Column('id', db.Integer, primary_key=True)
    value = db.Column('value', db.String)
    type = db.Column('type', db.String, unique=False)
    mangas = db.relationship('Manga', secondary='manga_tag', backref='tags')

    def __key(self):
        return (self.value, self.type)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.value == other.value and self.type == other.type