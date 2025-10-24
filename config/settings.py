# ==============================
# MongoDB Configuration
# ==============================
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "amazon_scraper"  
    # Database name

# ==============================
# Scraper Configuration
# ==============================
# Amazon search URL template — {query} will be replaced dynamically
SEARCH_URL = "https://www.amazon.in/s?k={query}"
    #It stores a string in this above variable.(which is a URL)
    #https=>Protocol
    #www.amazon.in=>Domain name
    #/s => amazon search page path
    #?k={query} => Query parameter , user what to search for .
    #?=> starts the query string in a URL
    #k= K is the parameter name uses for search keyword
    #{query} => placeholder for the actual search term.
    
# Run the browser in headless mode (True = no UI)
HEADLESS = True
#Use True show the browser UI while scraping , False will hide the browser UI.
#Use False show the browser UI while scraping , True will hide the browser UI.

# Optional: Default categories to scrape (used by main.py)
CATEGORIES = {
    "mobile": "mobiles",
    "laptop": "laptops",
    "sofa": "sofas",
    "toys": "toys",
    "shirts": "shirts",
}
