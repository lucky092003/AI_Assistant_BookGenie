from flask import Flask, jsonify, render_template, request, redirect, session, url_for
from pymongo import MongoClient
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "bookgenie_secret_key"
CORS(app)

# ===============================
# DATABASE
# ===============================
client = MongoClient("mongodb://localhost:27017/")
db = client["bookgenie_db"]

books_collection = db["books"]
users_collection = db["users"]
cart_collection = db["cart"]

users_collection.create_index("email", unique=True)

print("✅ MongoDB Connected Successfully")

# ===============================
# AUTH ROUTES
# ===============================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        if users_collection.find_one({"email": email}):
            return "User already exists"
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": password
        })
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            session["email"] = user["email"]
            return redirect(url_for("home"))
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ===============================
# HOME & BOOK ROUTES
# ===============================
@app.route("/")
def home():
    if "email" not in session:
        return redirect(url_for("login"))
    books = list(books_collection.find({}, {"_id": 0}).limit(50))
    return render_template("index.html", books=books)

@app.route("/book/<isbn>")
def book_details(isbn):
    if "email" not in session:
        return redirect(url_for("login"))
    book = books_collection.find_one({"isbn": isbn}, {"_id": 0})
    return render_template("details.html", book=book)

# ===============================
# CART PAGE ROUTE
# ===============================
@app.route("/cart")
def cart_page():
    if "email" not in session:
        return redirect(url_for("login"))

    # Fetch all cart items for the user
    items = list(cart_collection.find({"user_email": session["email"]}))
    total = sum(item["price"] for item in items)
    return render_template("cart.html", items=items, total=total)

# ===============================
# CART API
# ===============================
@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    # Fetch the book from books collection to store full details
    book = books_collection.find_one({"title": data["title"]})
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cart_collection.insert_one({
        "user_email": session["email"],
        "title": book["title"],
        "author": book["author"],
        "price": float(book.get("price", 449)),
        "isbn": book["isbn"],
        "image_url": book.get("image_url_m", "")
    })
    return jsonify({"success": True})

@app.route("/api/cart/remove", methods=["POST"])
def remove_cart_item():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    item_id = request.json.get("id")
    if not item_id:
        return jsonify({"error": "No item id provided"}), 400
    try:
        result = cart_collection.delete_one({
            "_id": ObjectId(item_id),
            "user_email": session["email"]
        })
        if result.deleted_count == 1:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cart/count")
def cart_count():
    if "email" not in session:
        return jsonify({"count": 0})
    count = cart_collection.count_documents({"user_email": session["email"]})
    return jsonify({"count": count})

@app.route("/api/cart/clear", methods=["POST"])
def clear_cart():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    cart_collection.delete_many({"user_email": session["email"]})
    return jsonify({"success": True})

# ===============================
# AI CHATBOT API
# ===============================
@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    if "email" not in session:
        return jsonify({"reply": "Please login first!"}), 401

    data = request.get_json()
    user_message = data.get("message", "")

    # TODO: Replace with OpenAI or any AI logic
    # Filhal simple echo for testing
    ai_reply = f"You said: {user_message}. (Genie replying!)"

    return jsonify({"reply": ai_reply})

# ===============================
if __name__ == "__main__":
    app.run(debug=True, port=3000)
