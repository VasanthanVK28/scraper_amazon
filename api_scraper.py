import asyncio
from fastapi import FastAPI
import uvicorn
from scraper.amazon_scraper import scrape_amazon

app = FastAPI()

@app.get("/scrape/{category}")
async def scrape_category(category: str):
    print(f"\n🔔 Admin requested scraping for category: {category}")

    # Use same naming logic as scheduler
    collection_name = f"{category.lower()}_collection"

    print(f"📌 Saving into MongoDB collection: {collection_name}")

    scraped = await scrape_amazon(
        query=category,
        collection_name=collection_name,
        max_products=5
    )

    return {
        "status": "success",
        "category": category,
        "collection": collection_name,
        "scraped": scraped
    }


if __name__ == "__main__":
    print("🚀 API Scraper Server running at http://127.0.0.1:9000")
    uvicorn.run(app, host="127.0.0.1", port=9000)
