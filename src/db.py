from flask_sqlalchemy import SQLAlchemy
import base64
import boto3
import datetime
import io
from io import BytesIO
from mimetypes import guess_extension, guess_type
import os
from PIL import Image
import random
import re
import string
import hashlib
import bcrypt

db = SQLAlchemy()

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com"


posters_to_categories_association_table = db.Table(
    "posters_to_categories_association",
    db.Model.metadata,
    db.Column("poster_id", db.Integer, db.ForeignKey("posters.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"))
)

students_to_categories_association_table = db.Table(
    "students_to_categories_association",
    db.Model.metadata,
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"))
)

posters_to_users_association_table = db.Table(
    "posters_to_users_association",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("poster_id", db.Integer, db.ForeignKey("posters.id"))
)

class Asset(db.Model):
    """
    Asset/Image Model
    Has a one-to-one relationship with posters(as the poster picture)
    Has a one-to-one relationship with users(as the user profile picture)
    """
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=True)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    poster_id = db.Column(db.Integer, db.ForeignKey('posters.id'))

    def __init__(self, **kwargs):
        """
        Initialize Asset object
        """
        self.user_id = kwargs.get("user_id")
        self.poster_id = kwargs.get("poster_id")
        self.create(kwargs.get("image_data"))

    def serialize(self):
        """
        Complete serialize for Asset object
        """
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at)
        }

    def create(self, image_data):
        """
        Given an image in bas64 form, does the following
        1. Rejects the image if it's not supported filetype
        2. Generates a random string for the image filename
        3. Decodes the image and attempts to upload it to AWS
        """
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]

            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} not supported")
            
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)
        except Exception as e:
            print(f"Error while creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempt to upload the image into an S3 bucket 
        """
        try:
            img_temploc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temploc)

            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET_NAME, img_filename)

            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            os.remove(img_temploc)
        except Exception as e:
            print(f"Error while uploading image: {e}")

    
class Poster(db.Model):
    """
    Poster model
    Has a one-to-one relationship with assets(poster picture)
    Has a one-to-many relationship with users(user has multiple created posters)
    Has a many-to-many relationship with users(user has saved multiple posters, posters have multiple users saved to)
    Has a many-to-many relationship with categories(poster can be under multiple categories, categories can be under multiple posters)
    """
    __tablename__ = "posters"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    number_of_likes = db.Column(db.Integer, nullable=False)
    number_of_views = db.Column(db.Integer, nullable=False)
    author = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    related_categories = db.relationship("Category", secondary=posters_to_categories_association_table, back_populates="posters_with_category")
    poster_pic = db.relationship('Asset', backref='poster', uselist=False)
    users_saved_to = db.relationship("User", secondary=posters_to_users_association_table, back_populates="saved_posters")

    def __init__(self, **kwargs):
        """
        Initialize Poster object
        """
        self.name = kwargs.get("name")
        self.number_of_likes = 0
        self.number_of_views = 0
        self.author = kwargs.get("author")
        self.date = kwargs.get("date")
        self.location = kwargs.get("location")
        self.description = kwargs.get("description")
        self.user_id = kwargs.get("user_id")

    def add_view(self, count):
        """
        Adds a certain number of views to view counter
        """
        self.number_of_views += count

    def add_like(self, count):
        """
        Adds a certain number of likes to like counter
        """
        self.number_of_likes += count

    def serialize(self):
        """
        Complete serialize of poster object
        """
        return {
            "id": self.id,
            "name": self.name,
            "number_of_likes": self.number_of_likes,
            "number_of_views": self.number_of_views,
            "author": self.author,
            "date": self.date.strftime("%Y-%m-%d %H:%M"),
            "location": self.location,
            "description": self.description,
            "user_id": self.user_id,
            "related_categories": [c.simple_serialize() for c in self.related_categories],
            "poster_pic": self.poster_pic.serialize(),
            "users_saved_to": [u.simple_serialize() for u in self.users_saved_to]
        }
    
    def simple_serialize(self):
        """
        Simple serialize for poster object
        """
        return {
            "id": self.id,
            "name": self.name,
            "number_of_likes": self.number_of_likes,
            "number_of_views": self.number_of_views,
            "author": self.author,
            "date": self.date.strftime("%Y-%m-%d %H:%M"),
            "location": self.location,
            "description": self.description,
            "user_id": self.user_id
        }


class User(db.Model):
    """
    User model
    Has a one-to-one relationship with assets(user has a profile picture)
    Has a one-to-many relationship with posters(user has multiple created posters)
    Has a many-to-many relationship with categories(user likes multiple categories, category liked by many users)
    Has a many-to-many relationship with posters(user saves multiple posters, posters have multiple users save it)
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    email = db.Column(db.String, nullable=False, unique=True)
    display_name = db.Column(db.String, nullable=False)
    password_digest = db.Column(db.String, nullable=False)

    session_token = db.Column(db.String, nullable=False, unique=False)
    session_expiration = db.Column(db.DateTime, nullable=False, unique=False)
    update_token = db.Column(db.String, nullable=False, unique=False)

    profile_pic = db.relationship('Asset', backref='user', uselist=False)
    my_posters = db.relationship("Poster", cascade="delete")
    interesting_categories = db.relationship("Category", secondary=students_to_categories_association_table, back_populates="users_with_category")
    saved_posters = db.relationship("Poster", secondary=posters_to_users_association_table, back_populates="users_saved_to")

    def __init__(self, **kwargs):
        """
        Intialize User object
        """
        self.email = kwargs.get("email")
        self.display_name = kwargs.get("display_name")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()

    def serialize(self):
        """
        Complete serialize of User object
        """
        pic = "None"
        if self.profile_pic is not None:
            pic = self.profile_pic.serialize()
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "profile_pic": pic,
            "my_posters": [p.simple_serialize() for p in self.my_posters],
            "interesting_categories": [c.simple_serialize() for c in self.interesting_categories],
            "saved_posters": [p.simple_serialize() for p in self.saved_posters]
        }

    def simple_serialize(self):
        """
        Simple serialize of User object
        """
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name
        }

    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token
    

class Category(db.Model):
    """
    Category model
    Has a many-to-many relationship with users(user likes multiple categories, each category has multiple users that like it)
    Has a many-to-many relationship with posters(poster has multiple related categories, each category has multiple related posters)
    """
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    posters_with_category = db.relationship("Poster", secondary=posters_to_categories_association_table, back_populates="related_categories")
    users_with_category = db.relationship("User", secondary=students_to_categories_association_table, back_populates="interesting_categories")
    
    def __init__(self, **kwargs):
        """
        Initialize Category object
        """
        self.title = kwargs.get("title")

    def simple_serialize(self):
        """
        Simple serialize of Category object
        """
        return {
            "id": self.id,
            "title": self.title
        }
    
    def serialize(self):
        """
        Complete serialize of Category object
        """
        return {
            "id": self.id,
            "title": self.title, 
            "posters_with_category": [p.simple_serialize() for p in self.posters_with_category],
            "users_with_category": [u.simple_serialize() for u in self.users_with_category]
        }
