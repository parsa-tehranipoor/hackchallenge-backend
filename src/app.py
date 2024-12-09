import json
import users_dao
import datetime

from db import db
from db import Asset
from db import Category
from db import Poster
from flask import Flask, request

db_filename = "challenge.db"
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


# generalized response formats
def success_response(data, code=200):
    """
    Generalized success response function
    """
    return json.dumps(data), code

def failure_response(message, code=404):
    """
    Generalized failure response function
    """
    return json.dumps({"error": message}), code

@app.route("/initialize/")
def initialize_app():
    """
    This initializes values in the app that are needed before it should run. You should only call this when the app is initially installed 
    """
    cat1 = Category(title="Design")
    cat2 = Category(title="Business")
    cat3 = Category(title="Art")
    cat4 = Category(title="Music")
    cat5 = Category(title="Sports")
    cat6 = Category(title="Computer Science")
    cat7 = Category(title="Chinese")
    cat8 = Category(title="Employment")
    cat9 = Category(title="Hiking")
    cat10 = Category(title="Nature")
    cat11 = Category(title="Culture")
    cat12 = Category(title="Food")
    cat13 = Category(title="Math")
    cat14 = Category(title="Movies")
    cat15 = Category(title="Concerts")

    db.session.add(cat1)
    db.session.add(cat2)
    db.session.add(cat3)
    db.session.add(cat4)
    db.session.add(cat5)
    db.session.add(cat6)
    db.session.add(cat7)
    db.session.add(cat8)
    db.session.add(cat9)
    db.session.add(cat10)
    db.session.add(cat11)
    db.session.add(cat12)
    db.session.add(cat13)
    db.session.add(cat14)
    db.session.add(cat15)

    db.session.commit()
    categories = Category.query.all()
    json_categories = []
    for category in categories:
        json_categories.append(category.serialize())
    return json.dumps(json_categories)

@app.route("/category/search/")
def search_for_category():
    """
    This allows the user to search for categories that they are interested in. The app will output all categories that begin with the string
    typed into the search bar. For example, "co" in the search bar will output "Computer Science" and "Concerts". Lowercase and Uppercase
    do not matter
    """
    body = json.loads(request.data)
    stringToSearch = body.get("search")
    if stringToSearch is None:
        return json.dumps({"error": "Invalid Body"})
    categories = Category.query.all()
    list = []
    for category in categories:
        if category.title.lower().startswith(stringToSearch.lower()):
            list.append(category.serialize())
    return json.dumps(list)

@app.route("/poster/<int:id>/")
def get_poster_from_id(id):
    """
    Gets a specific poster from its unique id
    """
    poster = Poster.query.filter_by(id=id).first()
    if poster is None:
        return json.dumps({"error": "Course not found!"})
    return json.dumps(poster.serialize())

@app.route("/poster/clicked/view/<int:id>/", methods=["POST"])
def seen_poster_for_first_time(id):
    """
    This method is called when a poster is seen for the first time by a user. It updates the posters view count by one and should ONLY
    be called the first time a user sees it.
    """
    poster = Poster.query.filter_by(id=id).first()
    if poster is None:
        return json.dumps({"error": "Course not found!"})
    poster.add_view(1)
    db.session.commit()
    return json.dumps(poster.serialize())

@app.route("/poster/clicked/likes/<int:id>/", methods=["POST"])
def added_to_likes(id):
    """
    When a user clicks the likes button, it increases Poster like count by 1
    """
    poster = Poster.query.filter_by(id=id).first()
    if poster is None:
        return json.dumps({"error": "Course not found!"})
    poster.add_like(1)
    db.session.commit()
    return json.dumps(poster.serialize())

@app.route("/poster/clicked/dislikes/<int:id>/", methods=["POST"])
def added_to_likes(id):
    """
    When a user clicks the likes button after just clicking it, it decreases Poster like count by 1
    """
    poster = Poster.query.filter_by(id=id).first()
    if poster is None:
        return json.dumps({"error": "Course not found!"})
    poster.add_like(-1)
    db.session.commit()
    return json.dumps(poster.serialize())

@app.route("/poster/clicked/save/<int:id>/", methods=["POST"])
def add_poster_to_saved(id):
    """
    Adds Poster to the Users saved list of Posters.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    poster = Poster.query.filter_by(id=id).first()
    if poster is None:
        return json.dumps({"error": "Course not found!"})
    for other_poster in user.saved_posters:
        if other_poster.id == id:
            return json.dumps({"error": "Already saved this poster"})
    user.saved_posters.append(poster)
    db.session.commit()
    return json.dumps(user.serialize())

@app.route("/user/posters/saved/upcoming/")
def sort_saved_posters_by_upcoming():
    """
    Finds all the saved posters that are upcoming in no particular order.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    upcoming = []
    for poster in user.saved_posters:
        if poster.date > datetime.datetime.now():
            upcoming.append(poster)
    return json.dumps(upcoming)

@app.route("/user/posters/saved/past/")
def sort_saved_posters_by_past():
    """
    Finds all the saved posters that have already occurred in no particular order.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    past = []
    for poster in user.saved_posters:
        if poster.date < datetime.datetime.now():
            past.append(poster)
    return json.dumps(past)

@app.route("/user/posters/owned/upcoming/")
def sort_my_posters_by_upcoming():
    """
    Finds all the users posters that are upcoming in no particular order.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    upcoming = []
    for poster in user.my_posters:
        if poster.date > datetime.datetime.now():
            upcoming.append(poster)
    return json.dumps(upcoming)

@app.route("/user/posters/owned/past/")
def sort_my_posters_by_past():
    """
    Finds all the users posters that already occurred in no particular order.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    past = []
    for poster in user.my_posters:
        if poster.date < datetime.datetime.now():
            past.append(poster)
    return json.dumps(past)

@app.route("/user/posters/poster", methods=["POST"])
def create_poster():
    """
    Creates a poster from a given body. Date needs to be in the specific format 'Y-m-d H:M'. Image_data should be base64, use the site
    https://www.base64-image.de/ to see what I mean.
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    body = json.loads(request.data)
    name = body.get("name")
    author = body.get("author")
    date = body.get("date")
    location = body.get("location")
    description = body.get("description")
    image_data = body.get("image_data")
    categories = body.get("categories")
    if name is None or author is None or date is None or location is None or description is None or image_data is None or categories is None:
        return json.dumps({"error": "Invalid Body"})
    date_format = "%Y-%m-%d %H:%M"

    try:
        datetime_object = datetime.datetime.strptime(date, date_format)
    except ValueError as e:
        json.dumps({"error": "Date object not understandable"})

    poster = Poster(name=name, author=author, date=datetime_object, location=location, description=description, user_id=user.id)
    db.session.add(poster)
    db.session.commit()
    asset = Asset(poster_id=poster.id, image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    all_categories = Category.query.all()
    for title in categories:
        for category in all_categories:
            if category.title == title:
                poster.related_categories.append(category)
    return json.dumps(poster.serialize())


def extract_token(request):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, json.dumps({"error": "Missing Authorization header"})
    
    # Bearer <token>
    bearer_token = auth_header.replace("Bearer", "").strip()
    if not bearer_token:
        return False, json.dumps({"error": "Invalid Authorization header"})
    return True, bearer_token

@app.route("/register/", methods=["POST"])
def register_account():
    """
    Endpoint for registering a new user. Does not require a user to have a profile picture
    """
    body = json.loads(request.data)
    email = body.get("email")
    display_name = body.get("display_name")
    password = body.get("password")
    image_data = body.get("image_data")
    if email is None or display_name is None or password is None:
        return json.dumps({"error": "Invalid Body"})
    
    created, user = users_dao.create_user(image_data, display_name, email, password)
    if not created:
        return json.dumps({"error": "User already exists"})
    
    return json.dumps({
        "session_token": user.session_token,
        "session_expireation": str(user.session_expiration),
        "update_token": user.update_token
    })


@app.route("/login/", methods=["POST"])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")

    if email is None or password is None:
        return json.dumps({"error": "Invalid Body"})
    
    success, user = users_dao.verify_credentials(email, password)
    if not success:
        return json.dumps({"error": "Invalid credentials"})
    
    user.renew_session()
    db.session.commit()
    return json.dumps({
        "session_token": user.session_token,
        "session_expireation": str(user.session_expiration),
        "update_token": user.update_token
    })


@app.route("/session/", methods=["POST"])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, response = extract_token(request)
    if not success:
        return response
    refresh_token = response

    try:
        user = users_dao.renew_session(refresh_token)
    except Exception as e:
        return json.dumps({"error": "Invalid refresh token"})
    
    return json.dumps({
        "session_token": user.session_token,
        "session_expireation": str(user.session_expiration),
        "update_token": user.update_token
    })


@app.route("/secret/", methods=["GET"])
def secret_message():
    """
    Endpoint for verifying a session token and returning a secret message

    In your project, you will use the same logic for any endpoint that needs 
    authentication
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    
    return json.dumps({"message": "hello "+user.display_name})

@app.route("/logout/", methods=["POST"])
def logout():
    """
    Endpoint for logging out a user
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response

    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    user.session_expiration = datetime.datetime.now()
    db.session.commit()
    return json.dumps({"message": "You have been logged out"})

@app.route("/upload/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No Base64 URL")
    
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
