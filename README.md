# 📚 BookGenie – AI-Powered Online Bookstore

🚀 **BookGenie** is a full-stack web application that combines e-commerce functionality with an AI-powered chatbot to provide an intelligent and interactive book browsing experience.

It allows users to search, explore, and purchase books while receiving real-time assistance through a conversational AI interface.

---

## 🌟 Features

* 🔍 **Smart Book Search** (Title / Author based)
* 📖 **Detailed Book View**
* 🛒 **Shopping Cart System**
* 👤 **User Authentication (Login/Signup)**
* 🧾 **Order Placement & Management**
* 🤖 **AI Chatbot (OpenAI / OpenRouter)**
* 👥 **Guest + Logged-in User Support**
* ⚡ **Fast & Dynamic UI with Flask + JS**

---

## 🧠 AI Chatbot System

* Uses **OpenAI / OpenRouter APIs**
* Handles natural language queries
* Hybrid architecture:

  * Intent-based responses (via dataset)
  * AI-generated responses (fallback)
* Can be extended with **DistilBERT model (included in notebook)**

---

## 🏗️ Tech Stack

### 🔹 Backend

* Python (Flask)
* PyMongo (MongoDB Driver)
* REST APIs

### 🔹 Frontend

* HTML, CSS, JavaScript

### 🔹 Database

* MongoDB (NoSQL)

### 🔹 AI / NLP

* OpenAI API / OpenRouter API
* Intent Classification (optional ML model)

---

## 📂 Project Structure

```bash
BookGenie/
│
├── data/
│   ├── Books.csv          # Dataset (28k+ books)
│   ├── intent.json        # Chatbot intents
│
├── notebook/
│   ├── intentModel.ipynb  # ML model (DistilBERT)
│
├── static/                # CSS, JS, assets
├── templates/             # HTML pages
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── cart.html
│   ├── details.html
│
├── import_books.py        # Load dataset into MongoDB
├── server.py              # Main Flask application
├── .env                   # API keys
└── README.md
```

---

## ⚙️ Setup & Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/lucky092003/AI_Assistant_BookGenie.git
cd AI_Assistant_BookGenie
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Setup MongoDB

* Install MongoDB locally
* Start MongoDB server
* Database auto-created: `bookgenie_db`

---

### 5️⃣ Configure Environment Variables

Create `.env` file:

```env
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key
USE_OPENROUTER=True
```

---

### 6️⃣ Load Dataset

```bash
python import_books.py
```

---

### 7️⃣ Run Application

```bash
python server.py
```

👉 Open in browser:

```
http://localhost:3000
```

---

## 🔗 API Endpoints

| Endpoint           | Description         |
| ------------------ | ------------------- |
| `/signup`          | Register user       |
| `/login`           | Login user          |
| `/search`          | Search books        |
| `/api/cart/add`    | Add to cart         |
| `/api/cart/remove` | Remove item         |
| `/api/cart/buy`    | Place order         |
| `/api/chatbot`     | Chatbot interaction |

---

## 🗄️ Database Collections

* 📚 `books` → Book dataset
* 👤 `users` → User accounts
* 🛒 `cart` → Cart items
* 🧾 `orders` → Order records
* 🔢 `counters` → Auto-increment IDs

---

## 🔐 Security Features

* 🔒 Password hashing (Werkzeug)
* 🔐 Session-based authentication
* 🛡️ Input validation (client + server)
* 🚫 Unauthorized access protection

---

## 📈 Future Improvements

* 🎯 Book Recommendation System (ML-based)
* 🔊 Voice Assistant (Speech-to-Text & TTS)
* 💳 Payment Gateway Integration
* 📱 Mobile Responsive UI
* 🧠 Advanced NLP chatbot (fine-tuned model)

---

## 👨‍💻 Author

**Lucky Patel**
GitHub: https://github.com/lucky092003

---

## ⭐ Support

If you like this project:

👉 Give it a ⭐ on GitHub
👉 Fork & contribute

---

## 📌 Project Highlights

* Full-stack AI-powered application
* Real-world e-commerce + chatbot integration
* Uses modern technologies (Flask + MongoDB + AI APIs)
* Scalable and modular architecture

---

💡 *"Combining AI with web development to create smarter user experiences."*
