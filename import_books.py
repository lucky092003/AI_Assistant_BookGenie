import pandas as pd
from pymongo import MongoClient
import random

# MongoDB connect
client = MongoClient("mongodb://localhost:27017/")
db = client["bookgenie_db"]
books_collection = db["books"]

# CSV path
csv_path = r"C:\Users\lucky\Desktop\BookGenie\data\Books.csv"

print("Reading CSV...")

# Read CSV
df = pd.read_csv(csv_path, low_memory=False)

# Rename columns
df = df.rename(columns={
    "ISBN": "isbn",
    "Book-Title": "title",
    "Book-Author": "author",
    "Year-Of-Publication": "year",
    "Publisher": "publisher",
    "Image-URL-S": "image_url_s",
    "Image-URL-M": "image_url_m",
    "Image-URL-L": "image_url_l"
})

# Remove empty titles
df = df.dropna(subset=["title"])

# ✅ ADD PRICE COLUMN HERE
df["price"] = [random.randint(100, 1000) for _ in range(len(df))]

print("Total books in CSV:", len(df))

# Convert to dictionary
books = df.to_dict("records")

# Clear old data
books_collection.delete_many({})

# Insert data
result = books_collection.insert_many(books)

print("Books inserted:", len(result.inserted_ids))

print("DONE ✅")
