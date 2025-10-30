MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "amazon_scraper"

HEADLESS = True  # Set False to watch browser

SEARCH_URL = "https://www.amazon.in/s?k={query}"

# You can map queries to specific collections
CATEGORIES = {
    "mobile": "mobiles",
    "laptop": "laptops",
    "sofa": "sofas",
    "shirt": "shirts",
    "toys": "toys",
}
