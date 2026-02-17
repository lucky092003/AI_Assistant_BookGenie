# 📚 BookGenie – AI-Powered Book Recommendation & Voice Assistant

## Overview
**BookGenie** is a modern web application designed for book enthusiasts. It combines book browsing, cart management, trending tags, and an AI-powered voice/chat assistant for personalized recommendations. Users can interact with the assistant via text or voice, manage their cart, and explore trending books and tags.

The project uses **Flask** for the backend, **MongoDB** for data storage, and a responsive frontend with HTML, CSS, and JavaScript.

---

## Features

### 1. User Authentication
- Secure signup and login with hashed passwords.
- User session management with Flask sessions.
- Logout functionality.

### 2. Book Browsing & Details
- Home page displays the latest 50 books.
- Search and view detailed information about books.
- Each book has a unique ISBN for detailed view.

### 3. Cart System
- Add books to the cart with full book details.
- Remove items or clear the cart.
- View total price of items in the cart.
- Persistent cart stored per user in MongoDB.

### 4. AI Chatbot & Voice Assistant
- Chatbot responds to user queries via text.
- Voice assistant integration using Web Speech API.
- Optional Speech-to-Text: Users can speak commands instead of typing.
- Personalized replies per user session.

### 5. Trending Tags
- Display tags trending based on user interactions and cart activity.
- Helps users explore popular books quickly.

### 6. Responsive & Professional UI
- Modern, clean interface with consistent color scheme.
- Fully responsive for desktop and mobile devices.

---

## Technology Stack

| Layer       | Technology                        |
|------------|----------------------------------|
| Backend     | Flask (Python)                   |
| Database    | MongoDB                           |
| Frontend    | HTML, CSS, JavaScript            |
| Voice/AI    | Web Speech API, OpenAI API (optional) |
| Dependencies| Flask-CORS, Werkzeug, PyMongo, OpenAI, Python-dotenv |

---
## Installation & Setup

### 1. Clone the Repository
git clone <your-repo-url>
cd BookGenie

### 2. Create Virtual Environment

Create a Python virtual environment to manage dependencies:
#### 2.1 Create virtual environment
python -m venv venv

#### 2.2 Activate virtual environment
#### On Windows (Command Prompt)
venv\Scripts\activate
#### 2.3 On Windows (PowerShell)
venv\Scripts\Activate.ps1

### 3. Import The data
python import_books.py

### 4. Run the Application
python server.py

### 5. Run Local host 
http://localhost:3000/

## Environment Variables
OPENAI_API_KEY = "openAI_API_Key"

---

---
###  Folder Structure 
BookGenie/
│
├── data/
│ └── Books.csv # Sample books dataset
├── static/
│ ├── css/
│ │ └── style.css # Stylesheets
│ └── js/
│ └── script.js # Frontend JS
├── templates/
│ ├── index.html # Home page
│ ├── cart.html # Cart page
│ ├── details.html # Book details page
│ ├── login.html # Login page
│ ├── signup.html # Signup page
│ └── privacy.html # Privacy policy page
├── venv/ # Python virtual environment
├── .env # Environment variables
├── import_books.py # Script to import books from CSV
├── server.py # Flask backend with routes & APIs
└── README.md # Project documentation

---