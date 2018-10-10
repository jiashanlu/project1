import os

from flask import Flask, session, render_template, url_for, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
import requests
import json

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    search = []
    if request.method == "POST":
        get_search = '%' + request.form.get("search") +'%'
        search = db.execute("SELECT * FROM books WHERE isbn iLIKE :search OR title iLIKE :search \
        OR author iLIKE :search LIMIT 10",{"search": get_search}).fetchall()
    return render_template("search.html", searched=search)

@app.route("/book/<int:book_id>", methods=["GET", "POST"])
def book(book_id):
    book=db.execute("SELECT * FROM books WHERE id = :book_id",{"book_id": book_id}).fetchone()
    if request.method == "POST":
        db.execute("INSERT INTO reviews (review, books_id, users_id, rating)\
        VALUES (:review, :books_id, :users_id, :rating) ON CONFLICT (users_id, books_id)\
        DO UPDATE SET (review, books_id, users_id, rating) = (EXCLUDED.review, EXCLUDED.books_id,\
        EXCLUDED.users_id, EXCLUDED.rating)",{"review": request.form.get("review"), \
        "books_id": book[0],"users_id": session['logged_in'][0], "rating": request.form.get("rating")})
        db.commit()
    reviews_done = db.execute("SELECT * FROM users JOIN reviews ON users.id = users_id WHERE \
    books_id = :books_id", {"books_id": book[0]}).fetchall()
    my_review = db.execute("SELECT * FROM reviews WHERE books_id = :books_id \
    AND users_id= :users_id", {"books_id": book[0], "users_id": session['logged_in'][0]}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "8hTmKo3qFBgYy9Oc2yDLQ", "isbns": book[1]})
    return render_template("book.html", book=book, reviews=reviews_done, my_review=my_review, res=res.json())


@app.route("/login", methods=["GET", "POST"])
def login():
    message = []
    if session['logged_in'] is None :
        session['logged_in'] = False
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        pseudo = db.execute("SELECT * FROM users WHERE pseudo = :username",{"username": username}).fetchone()
        hash = db.execute("SELECT password FROM users WHERE pseudo = :username",{"username": username}).fetchone()
        if not pseudo:
            message = "user does not exist"
        elif sha256_crypt.verify(request.form.get("password"), hash[0]):
            session['logged_in'] = db.execute("SELECT * FROM users WHERE pseudo = :username",{"username": username}).fetchone()
            message = "succesufly logged-in"
            return render_template("search.html")
        else:
            message = "wrong password"
    return render_template("login.html", message=message, id=session['logged_in'])

@app.route("/logout", methods=["GET"])
def logout():
    message = "logged out"
    session['logged_in'] = False
    return render_template("login.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    message = []
    if request.method == "POST":
        username = request.form.get("username")
        password = sha256_crypt.encrypt(request.form.get("password"))
        email = request.form.get("email")
        fullname=request.form.get("fullname")
        gender=request.form.get("gender")
        if sha256_crypt.verify(request.form.get("password2"), password) and request.form.get("agree")=="agree" :
            db.execute("INSERT INTO users (pseudo, password, email, fullname, gender)\
            VALUES (:username , :password, :email, :fullname, :gender)",\
            {"username": username, "password": password, "email": email, "fullname": fullname, "gender": gender})
            db.commit()
            message = "sucess! please login"
        else :
            message = "something wrong"
    return render_template("register.html", message=message)

@app.route("/api/<ISBN>", methods=["GET", "POST"])
def books_api(ISBN):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn": ISBN}).fetchone()
    review_count = db.execute("SELECT COUNT(review) FROM reviews WHERE books_id = :books_id",{"books_id": book.id}).fetchone()
    review_average = db.execute("SELECT AVG(rating) FROM reviews WHERE books_id = :books_id",{"books_id": book.id}).fetchone()
    if book is None:
        return jsonify({"error": "not in database"}), 404
    return jsonify({
        "ISBN": book.isbn,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "review_count" : review_count[0],
        "review_average" : str(review_average[0]),
        })
