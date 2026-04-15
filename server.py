from flask import Flask, jsonify, render_template, request, redirect, session, url_for
from pymongo import MongoClient, ReturnDocument
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import os
import requests
import openai
from dotenv import load_dotenv
from datetime import datetime
from threading import Lock
import re

# ===============================
# LOAD ENV
# ===============================
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "True").lower() == "true"

# ===============================
# FLASK APP INIT
# ===============================
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
orders_collection = db["orders"]
counters_collection = db["counters"]

users_collection.create_index("email", unique=True)

print(" MongoDB Connected Successfully")

# ===============================
# CHATBOT REQUEST STATE
# ===============================
chat_lock = Lock()
chat_stop_flags = {}


def get_chat_key():
    if "user_id" in session:
        return f"user:{session['user_id']}"
    return f"guest:{request.remote_addr}:{request.headers.get('User-Agent', '')}"


def get_relevant_books(user_message, limit=8):
    tokens = [
        token for token in re.findall(r"[A-Za-z0-9']+", user_message.lower())
        if len(token) >= 3
    ]
    projection = {
        "_id": 0,
        "title": 1,
        "author": 1,
        "isbn": 1,
        "price": 1,
        "publisher": 1,
        "year": 1
    }

    if tokens:
        pattern = "|".join(re.escape(token) for token in tokens[:6])
        query = {
            "$or": [
                {"title": {"$regex": pattern, "$options": "i"}},
                {"author": {"$regex": pattern, "$options": "i"}},
                {"publisher": {"$regex": pattern, "$options": "i"}}
            ]
        }
        books = list(books_collection.find(query, projection).limit(limit))
    else:
        books = []

    if not books:
        books = list(books_collection.find({}, projection).limit(limit))

    for book in books:
        book["price"] = float(book.get("price", 449))

    return books


def get_user_chat_context():
    if "email" not in session:
        return {
            "user": "guest",
            "is_logged_in": False,
            "cart_items": session.get("guest_cart", []),
            "cart_count": len(session.get("guest_cart", [])),
            "recent_orders": [],
            "purchased_titles": [],
            "note": "Guest user. Ask them to login for account-specific order history."
        }

    user_email = session["email"]
    cart_items = list(cart_collection.find(
        {"user_email": user_email},
        {"_id": 0, "title": 1, "author": 1, "price": 1, "isbn": 1}
    ))

    recent_orders = list(orders_collection.find(
        {"user_email": user_email},
        {"_id": 0, "items": 1, "total_amount": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5))

    purchased_titles = []
    for order in recent_orders:
        for item in order.get("items", []):
            title = item.get("title")
            if title:
                purchased_titles.append(title)

    # Preserve order while removing duplicates.
    purchased_titles = list(dict.fromkeys(purchased_titles))

    return {
        "user": session.get("user", "user"),
        "is_logged_in": True,
        "email": user_email,
        "cart_items": cart_items,
        "cart_count": len(cart_items),
        "recent_orders": recent_orders,
        "purchased_titles": purchased_titles,
        "note": "Use this data for personalized cart/order answers."
    }

# ===============================
# AUTO INCREMENT FUNCTION
# ===============================
def get_next_user_id():
    counter = counters_collection.find_one_and_update(
        {"_id": "user_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,  # create if not exists
        return_document=ReturnDocument.AFTER
    )
    return counter["sequence_value"]

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

        new_user_id = get_next_user_id()

        users_collection.insert_one({
            "user_id": new_user_id,
            "username": username,
            "email": email,
            "password": password,
            "created_at": datetime.utcnow()
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
            session["user_id"] = user["user_id"]
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ===============================
# HOME
# ===============================
@app.route("/")
def home():
    books = list(books_collection.find({}, {"_id": 0}).limit(50))
    user = session.get("user")
    is_guest = user is None

    return render_template(
        "index.html",
        books=books,
        user=user,
        is_guest=is_guest
    )

# ===============================
# BOOK DETAILS
# ===============================
@app.route("/book/<isbn>")
def book_details(isbn):
    book = books_collection.find_one({"isbn": isbn}, {"_id": 0})
    return render_template("details.html", book=book)


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "")  # URL me ?q=search_term
    if not query:
        return redirect(url_for("home"))

    # case-insensitive search on title or author
    books = list(books_collection.find(
        {"$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"author": {"$regex": query, "$options": "i"}}
        ]},
        {"_id": 0}
    ).limit(50))

    user = session.get("user")
    is_guest = user is None

    return render_template("index.html", books=books, user=user, is_guest=is_guest)
# ===============================
# CART PAGE
# ===============================
@app.route("/cart")
def cart_page():

    if "email" in session:
        items = list(cart_collection.find({"user_email": session["email"]}))
    else:
        items = session.get("guest_cart", [])

    total = sum(float(item["price"]) for item in items)

    return render_template("cart.html", items=items, total=total)

# ===============================
# ADD TO CART
# ===============================
@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():

    data = request.json
    book = books_collection.find_one({"title": data["title"]})

    if not book:
        return jsonify({"error": "Book not found"}), 404

    cart_item = {
        "title": book["title"],
        "author": book["author"],
        "price": float(book.get("price", 449)),
        "isbn": book["isbn"],
        "image_url": book.get("image_url_m", "")
    }

    if "email" in session:
        cart_item["user_email"] = session["email"]
        cart_collection.insert_one(cart_item)
    else:
        guest_cart = session.get("guest_cart", [])
        guest_cart.append(cart_item)
        session["guest_cart"] = guest_cart

    return jsonify({"success": True})

# ===============================
# REMOVE FROM CART
# ===============================
@app.route("/api/cart/remove", methods=["POST"])
def remove_cart_item():

    item_id = request.json.get("id")

    if "email" in session:
        cart_collection.delete_one({
            "_id": ObjectId(item_id),
            "user_email": session["email"]
        })
    else:
        guest_cart = session.get("guest_cart", [])
        guest_cart = [item for item in guest_cart if item["isbn"] != item_id]
        session["guest_cart"] = guest_cart

    return jsonify({"success": True})

# ===============================
# CART COUNT
# ===============================
@app.route("/api/cart/count")
def cart_count():

    if "email" in session:
        count = cart_collection.count_documents({"user_email": session["email"]})
    else:
        count = len(session.get("guest_cart", []))

    return jsonify({"count": count})

# ===============================
# CLEAR CART
# ===============================
@app.route("/api/cart/clear", methods=["POST"])
def clear_cart():

    if "email" in session:
        cart_collection.delete_many({"user_email": session["email"]})
    else:
        session["guest_cart"] = []

    return jsonify({"success": True})

# ===============================
# BUY CART
# ===============================
@app.route("/api/cart/buy", methods=["POST"])
def buy_cart():

    if "email" not in session:
        return jsonify({
            "success": False,
            "message": "Please login to continue"
        }), 401

    user_email = session["email"]

    items = list(cart_collection.find({"user_email": user_email}))

    if not items:
        return jsonify({
            "success": False,
            "message": "Your cart is empty"
        }), 400

    order = {
        "user_email": user_email,
        "items": items,
        "total_amount": sum(float(item["price"]) for item in items),
        "created_at": datetime.utcnow()
    }

    orders_collection.insert_one(order)
    cart_collection.delete_many({"user_email": user_email})

    return jsonify({
        "success": True,
        "message": "Order placed successfully 🎉"
    })

# ===============================
# CHATBOT
# ===============================
@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"reply": "Please type something.", "stopped": False}), 400

    chat_key = get_chat_key()

    with chat_lock:
        chat_stop_flags[chat_key] = False

    books_context = get_relevant_books(user_message)
    user_context = get_user_chat_context()

    context_message = {
        "user_context": user_context,
        "relevant_books": books_context
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are BookGenie AI assistant for a bookstore app. "
                "Use the provided context to answer questions about books, cart, and orders. "
                "If user asks account-specific info and not logged in, ask them to login. "
                "Do not invent cart/order data not present in context. "
                "Keep replies short, clear, and user-friendly."
            )
        },
        {
            "role": "system",
            "content": f"Context data: {context_message}"
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    try:
        with chat_lock:
            if chat_stop_flags.get(chat_key):
                return jsonify({"reply": "Stopped.", "stopped": True})

        if USE_OPENROUTER:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages
            }

            response = requests.post(url, json=payload, headers=headers, timeout=45)
            response.raise_for_status()
            body = response.json()
            reply = body.get("choices", [{}])[0].get("message", {}).get("content", "No response")

        else:
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            reply = response.choices[0].message.content

        with chat_lock:
            if chat_stop_flags.get(chat_key):
                return jsonify({"reply": "Stopped.", "stopped": True})

    except Exception as e:
        reply = f"Error: {str(e)}"

    return jsonify({"reply": reply, "stopped": False})


@app.route("/api/chatbot/stop", methods=["POST"])
def chatbot_stop():
    chat_key = get_chat_key()
    with chat_lock:
        chat_stop_flags[chat_key] = True
    return jsonify({"success": True, "message": "Chat stopped"})

# ===============================
if __name__ == "__main__":
    app.run(debug=True, port=3000)