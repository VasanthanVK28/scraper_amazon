import asyncio
from scraper.amazon_scraper import scrape_amazon
from config.settings import CATEGORIES

async def main():
    for query, collection in CATEGORIES.items():
        print(f"\n🚀 Starting scrape for '{query}' → collection '{collection}'")
        await scrape_amazon(query, collection_name=collection, max_pages=5)
        print(f"✅ Finished scraping {query}\n")

if __name__ == "__main__":
    asyncio.run(main())
    print("🎉 All scraping tasks completed successfully!")
