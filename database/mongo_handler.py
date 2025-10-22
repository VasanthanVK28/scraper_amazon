# database/mongo_handler.py

from datetime import datetime
import pymongo
from config.settings import MONGO_URI, DB_NAME, COLLECTION_NAME

# Create a MongoDB client
client = pymongo.MongoClient(MONGO_URI)

# Select the database and collection
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def upsert_product(doc: dict):
    """
    Insert or update a product document in MongoDB.
    Uses the ASIN as the unique identifier.
    If the ASIN already exists, update the document with new values.
    """
    asin = doc.get("asin")
    title = doc.get("title")
    price = doc.get("price")

    if asin and title and price:
        collection.update_one(
            {"asin": asin},
            {"$set": {
                "title": title,
                "price": price,
                "rating": doc.get("rating"),
                "reviews": doc.get("reviews"),
                "image_url": doc.get("image_url"),
                "product_url": doc.get("product_url"),
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"✅ Stored: {title} | ASIN: {asin}")
    else:
        print(f"⚠️ Skipping incomplete product: ASIN={asin}, Title={title}")

def get_product_by_asin(asin: str):
    """Retrieve a single product by its ASIN."""
    return collection.find_one({"asin": asin})

def get_all_products(limit: int = 50):
    """Retrieve all products, with an optional limit."""
    return list(collection.find().limit(limit))

def delete_product(asin: str):
    """Delete a product by its ASIN."""
    collection.delete_one({"asin": asin})

def clear_collection():
    """Delete all documents in the collection."""
    collection.delete_many({})