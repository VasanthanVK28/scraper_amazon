from datetime import datetime
import pymongo
from zoneinfo import ZoneInfo   # Requires Python 3.9+ and tzdata installed
from config.settings import MONGO_URI, DB_NAME

# --- MongoDB Client & Database ---
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

# --- Timezone (IST) ---
IST = ZoneInfo("Asia/Kolkata")

# --- Collection Helpers ---
def get_collection(name: str):
    """Return a MongoDB collection by name."""
    return db[name]

def ensure_indexes(collection_name: str):
    """
    Ensure unique index on ASIN for faster upserts.
    Call this once per collection at startup.
    """
    collection = db[collection_name]
    try:
        collection.create_index("asin", unique=True)
        print(f"✅ Index ensured on '{collection_name}' (asin)")
    except Exception as e:
        print(f"❌ Failed to create index on '{collection_name}': {e}")

# --- Upsert Logic ---
def upsert_product(doc: dict, collection_name: str):
    """
    Insert or update a product document in MongoDB.
    Uses the ASIN as the unique identifier within the given collection.
    """
    asin = doc.get("asin")
    title = doc.get("title")
    price = doc.get("price")

    if asin and title and price:
        collection = db[collection_name]

        # Normalize optional fields
        rating = doc.get("rating") or 0.0
        reviews = doc.get("reviews") or 0
        image_url = doc.get("image_url") or "https://via.placeholder.com/150"
        product_url = doc.get("product_url") or f"https://www.amazon.in/dp/{asin}"
        tags = doc.get("tags") or []  # ✅ NEW FIELD
        brand = doc.get("brand") or "Unknown"

        doc_to_store = {
            "asin": asin,
            "title": title,
            "price": price,
            "rating": rating,
            "reviews": reviews,
            "image_url": image_url,
            "product_url": product_url,
            "tags": tags,  # ✅ Include tags
            "brand": brand,
            "last_updated": datetime.now(IST).isoformat()
            
        }

        try:
            collection.update_one({"asin": asin}, {"$set": doc_to_store}, upsert=True)
            print(f"✅ Stored in '{collection_name}': {title} | ASIN: {asin} | Brand: {brand}")
        except Exception as e:
            print(f"❌ MongoDB error for ASIN={asin}: {e}")
    else:
        print(f"⚠️ Skipping incomplete product: ASIN={asin}, Title={title}")

# --- Connection Cleanup ---
def close_connection():
    """Close MongoDB connection (optional for long-running apps)."""
    client.close()
