from flask import Flask, jsonify, render_template, request, redirect, session, url_for
from pymongo import MongoClient, ReturnDocument
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import json
import os
import pickle
import random
import re
import requests
import openai
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

import torch
from safetensors.torch import load_file as safetensors_load_file
from transformers import AutoConfig, AutoTokenizer, DistilBertForSequenceClassification

# ===============================
# LOAD ENV
# ===============================
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "True").lower() == "true"
INTENT_FILE = Path(__file__).with_name("data").joinpath("intent.json")
INTENT_MODEL_DIR = Path(__file__).with_name("notebook").joinpath("intent_model")
INTENT_MODEL_WEIGHTS = Path(__file__).with_name("model.safetensors")
INTENT_LABEL_ENCODER_FILE = Path(__file__).with_name("notebook").joinpath("label_encoder.pkl")
INTENT_MODEL_THRESHOLD = float(os.getenv("INTENT_MODEL_THRESHOLD", "0.65"))
BOOKS_PER_PAGE = int(os.getenv("BOOKS_PER_PAGE", "20"))

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

print("✅ MongoDB Connected Successfully")

# ===============================
# CHATBOT INTENTS
# ===============================
def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_intents():
    try:
        with INTENT_FILE.open("r", encoding="utf-8") as file:
            return json.load(file).get("intents", [])
    except Exception as exc:
        print(f"⚠️ Could not load chatbot intents: {exc}")
        return []


INTENTS = load_intents()


def detect_intent(user_message):
    normalized_message = normalize_text(user_message)
    if not normalized_message:
        return None

    message_tokens = set(normalized_message.split())
    best_match = None
    best_score = 0.0

    for intent in INTENTS:
        if intent.get("tag") == "fallback":
            continue

        patterns = intent.get("patterns", [])
        for pattern in patterns:
            normalized_pattern = normalize_text(pattern)
            if not normalized_pattern:
                continue

            if normalized_pattern == normalized_message:
                score = 2.0
            elif normalized_pattern in normalized_message and len(normalized_pattern.split()) >= 2:
                score = 1.1
            else:
                pattern_tokens = set(normalized_pattern.split())
                if not pattern_tokens:
                    continue
                shared_tokens = len(message_tokens & pattern_tokens)
                pattern_coverage = shared_tokens / len(pattern_tokens)
                message_coverage = shared_tokens / len(message_tokens)

                # Allow short queries like "need help" to match longer training patterns
                # such as "i need help" when most user words are covered.
                if (
                    (pattern_coverage >= 0.8 and shared_tokens >= 2) or
                    (len(message_tokens) <= 3 and message_coverage >= 0.9 and shared_tokens >= 2)
                ):
                    score = max(pattern_coverage, message_coverage)
                else:
                    score = 0

            if score > best_score:
                best_score = score
                best_match = intent

    if best_match and best_score >= 0.75:
        return best_match

    return None


def get_intent_reply(intent):
    responses = intent.get("responses", [])
    if responses:
        return random.choice(responses)
    return None


def get_intent_by_tag(tag):
    for intent in INTENTS:
        if intent.get("tag") == tag:
            return intent
    return None


def load_intent_model():
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(INTENT_MODEL_DIR), local_files_only=True)
        config = AutoConfig.from_pretrained(str(INTENT_MODEL_DIR), local_files_only=True)
        model = DistilBertForSequenceClassification(config)

        if not INTENT_MODEL_WEIGHTS.exists():
            raise FileNotFoundError(f"Weights not found: {INTENT_MODEL_WEIGHTS}")

        state_dict = safetensors_load_file(str(INTENT_MODEL_WEIGHTS))
        model.load_state_dict(state_dict, strict=False)

        with INTENT_LABEL_ENCODER_FILE.open("rb") as file:
            label_encoder = pickle.load(file)

        labels = [str(label) for label in label_encoder.classes_]
        model.eval()
        print("✅ Intent model loaded successfully")
        return tokenizer, model, labels
    except Exception as exc:
        print(f"⚠️ Intent model disabled: {exc}")
        return None, None, []


INTENT_TOKENIZER, INTENT_MODEL, INTENT_LABELS = load_intent_model()


def detect_intent_with_model(user_message):
    if not INTENT_TOKENIZER or not INTENT_MODEL or not INTENT_LABELS:
        return None, 0.0

    normalized_message = normalize_text(user_message)
    if not normalized_message:
        return None, 0.0

    encoded = INTENT_TOKENIZER(
        normalized_message,
        truncation=True,
        max_length=128,
        return_tensors="pt"
    )

    with torch.no_grad():
        logits = INTENT_MODEL(**encoded).logits
        probabilities = torch.softmax(logits, dim=-1)[0]
        confidence, predicted_index = torch.max(probabilities, dim=0)

    predicted_idx = int(predicted_index.item())
    if predicted_idx >= len(INTENT_LABELS):
        return None, 0.0

    predicted_tag = INTENT_LABELS[predicted_idx]
    confidence_score = float(confidence.item())

    if confidence_score < INTENT_MODEL_THRESHOLD or predicted_tag == "fallback":
        return None, confidence_score

    return get_intent_by_tag(predicted_tag), confidence_score


def get_acknowledgement_reply(user_message):
    normalized = normalize_text(user_message)
    if normalized in {"ok", "okay", "k", "alright", "fine", "got it"}:
        return "Great. If you want, I can also help you open your cart, add books, or checkout."
    return None


def is_cart_books_query(user_message):
    normalized = normalize_text(user_message)
    cart_phrases = {
        "in my cart",
        "my cart",
        "cart items",
        "books in my cart"
    }
    if any(phrase in normalized for phrase in cart_phrases):
        return True

    tokens = set(normalized.split())
    return "cart" in tokens and bool(tokens & {"which", "what", "show", "list", "books", "items"})


def is_purchased_books_query(user_message):
    normalized = normalize_text(user_message)
    purchase_phrases = {
        "which books i buyed",
        "which books i bought",
        "what books i bought",
        "my purchased books",
        "books i purchased",
        "books i ordered",
        "order history"
    }
    if any(phrase in normalized for phrase in purchase_phrases):
        return True

    tokens = set(normalized.split())
    return bool(tokens & {"bought", "buyed", "purchased", "ordered"}) and "books" in tokens


def get_cart_books_reply():
    if "email" in session:
        items = list(cart_collection.find({"user_email": session["email"]}, {"title": 1, "_id": 0}))
    else:
        items = session.get("guest_cart", [])

    titles = [item.get("title") for item in items if item.get("title")]
    if not titles:
        return "Your cart is currently empty."

    unique_titles = list(dict.fromkeys(titles))
    preview = ", ".join(unique_titles[:8])
    if len(unique_titles) > 8:
        preview += ", ..."

    return f"These books are currently in your cart: {preview}."


def get_purchased_books_reply():
    if "email" not in session:
        return "Please login to view books you have purchased."

    orders = list(
        orders_collection.find(
            {"user_email": session["email"]},
            {"items.title": 1, "_id": 0}
        ).sort("created_at", -1).limit(10)
    )

    titles = []
    for order in orders:
        for item in order.get("items", []):
            title = item.get("title")
            if title:
                titles.append(title)

    if not titles:
        return "I could not find any purchased books in your order history yet."

    unique_titles = list(dict.fromkeys(titles))
    preview = ", ".join(unique_titles[:10])
    if len(unique_titles) > 10:
        preview += ", ..."

    return f"You have purchased these books: {preview}."


def extract_openrouter_reply(response):
    response_data = response.json()
    choices = response_data.get("choices")

    if choices and isinstance(choices, list):
        message = choices[0].get("message", {})
        content = message.get("content")
        if content:
            return content

    provider_error = response_data.get("error", {})
    provider_message = provider_error.get("message") if isinstance(provider_error, dict) else None
    if provider_message:
        raise ValueError(provider_message)

    raise ValueError("LLM response did not contain choices")


def build_system_prompt(matched_intent=None):
    base_prompt = "You are BookGenie, a helpful bookstore assistant. Respond clearly and concisely."
    if matched_intent:
        return (
            f"{base_prompt} "
            f"The detected intent is '{matched_intent.get('tag', 'unknown')}'. "
            f"Answer in a way that matches that intent and stays focused on the bookstore context."
        )
    return base_prompt


def ask_openrouter(user_message, system_prompt):
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return extract_openrouter_reply(response)


def ask_openai(user_message, system_prompt):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    # Supports latest OpenAI SDK while keeping backward compatibility.
    if hasattr(openai, "OpenAI"):
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content

    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content


def get_llm_reply_with_failover(user_message, matched_intent=None):
    system_prompt = build_system_prompt(matched_intent)
    errors = []

    provider_order = ["openrouter", "openai"] if USE_OPENROUTER else ["openai", "openrouter"]

    for provider in provider_order:
        try:
            if provider == "openrouter":
                return ask_openrouter(user_message, system_prompt)
            return ask_openai(user_message, system_prompt)
        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    raise RuntimeError(" | ".join(errors) if errors else "No LLM provider available")


def get_current_page():
    page_raw = request.args.get("page", "1")
    try:
        return max(int(page_raw), 1)
    except (TypeError, ValueError):
        return 1


def get_catalog_filters_from_request():
    return {
        "title": request.args.get("title", "").strip(),
        "author": request.args.get("author", "").strip(),
        "year": request.args.get("year", "").strip(),
        "publisher": request.args.get("publisher", "").strip(),
    }


def build_catalog_filter(search_query="", title="", author="", year="", publisher=""):
    conditions = []

    if search_query:
        conditions.append({
            "$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"author": {"$regex": search_query, "$options": "i"}}
            ]
        })

    if title:
        conditions.append({"title": {"$regex": title, "$options": "i"}})
    if author:
        conditions.append({"author": {"$regex": author, "$options": "i"}})
    if year:
        conditions.append({"year": {"$regex": year, "$options": "i"}})
    if publisher:
        conditions.append({"publisher": {"$regex": publisher, "$options": "i"}})

    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def get_page_numbers(page, total_pages, window_size=5):
    window_size = max(window_size, 1)
    half = window_size // 2

    start_page = max(page - half, 1)
    end_page = min(start_page + window_size - 1, total_pages)

    if end_page - start_page + 1 < window_size:
        start_page = max(end_page - window_size + 1, 1)

    return list(range(start_page, end_page + 1))

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
    page = get_current_page()
    filters = get_catalog_filters_from_request()
    book_filter = build_catalog_filter(
        title=filters["title"],
        author=filters["author"],
        year=filters["year"],
        publisher=filters["publisher"]
    )

    total_books = books_collection.count_documents(book_filter)
    total_pages = max((total_books + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE, 1)

    if page > total_pages:
        page = total_pages

    skip = (page - 1) * BOOKS_PER_PAGE
    books = list(
        books_collection.find(book_filter, {"_id": 0})
        .skip(skip)
        .limit(BOOKS_PER_PAGE)
    )

    user = session.get("user")
    is_guest = user is None

    return render_template(
        "index.html",
        books=books,
        user=user,
        is_guest=is_guest,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        page_numbers=get_page_numbers(page, total_pages),
        is_search=False,
        search_query="",
        title_filter=filters["title"],
        author_filter=filters["author"],
        year_filter=filters["year"],
        publisher_filter=filters["publisher"]
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
    query = request.args.get("q", "").strip()  # URL me ?q=search_term
    if not query:
        return redirect(url_for("home"))

    page = get_current_page()
    filters = get_catalog_filters_from_request()
    book_filter = build_catalog_filter(
        search_query=query,
        title=filters["title"],
        author=filters["author"],
        year=filters["year"],
        publisher=filters["publisher"]
    )

    total_books = books_collection.count_documents(book_filter)
    total_pages = max((total_books + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE, 1)

    if page > total_pages:
        page = total_pages

    skip = (page - 1) * BOOKS_PER_PAGE

    # case-insensitive search on title or author
    books = list(
        books_collection.find(book_filter, {"_id": 0})
        .skip(skip)
        .limit(BOOKS_PER_PAGE)
    )

    user = session.get("user")
    is_guest = user is None

    return render_template(
        "index.html",
        books=books,
        user=user,
        is_guest=is_guest,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        page_numbers=get_page_numbers(page, total_pages),
        is_search=True,
        search_query=query,
        title_filter=filters["title"],
        author_filter=filters["author"],
        year_filter=filters["year"],
        publisher_filter=filters["publisher"]
    )
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
    user_message = data.get("message", "")

    ack_reply = get_acknowledgement_reply(user_message)
    if ack_reply:
        return jsonify({"reply": ack_reply, "intent": "acknowledgement"})

    if is_cart_books_query(user_message):
        return jsonify({"reply": get_cart_books_reply(), "intent": "view_cart"})

    if is_purchased_books_query(user_message):
        return jsonify({"reply": get_purchased_books_reply(), "intent": "order_status"})

    # Priority: trained model intent -> heuristic intent -> LLM fallback
    model_intent, model_confidence = detect_intent_with_model(user_message)
    heuristic_intent = detect_intent(user_message)

    if model_intent and heuristic_intent:
        if model_intent.get("tag") != heuristic_intent.get("tag") and model_confidence < 0.9:
            matched_intent = heuristic_intent
        else:
            matched_intent = model_intent
    else:
        matched_intent = model_intent or heuristic_intent

    if matched_intent:
        intent_reply = get_intent_reply(matched_intent)
        if intent_reply:
            return jsonify({
                "reply": intent_reply,
                "intent": matched_intent.get("tag", "")
            })

    try:
        reply = get_llm_reply_with_failover(user_message, matched_intent)
    except Exception as e:
        if matched_intent:
            reply = get_intent_reply(matched_intent) or f"Error: {str(e)}"
        else:
            reply = "I am having trouble reaching the AI service right now. Please try again in a moment."

    response_data = {"reply": reply}
    if matched_intent:
        response_data["intent"] = matched_intent.get("tag", "")
    return jsonify(response_data)

# ===============================
if __name__ == "__main__":
    app.run(debug=True, port=3000)