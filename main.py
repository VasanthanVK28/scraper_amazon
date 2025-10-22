import asyncio
from scraper.amazon_scraper import scrape_amazon

if __name__ == "__main__":
    asyncio.run(scrape_amazon("mobile"))
    print("🎉 Scraping finished. Data stored in MongoDB.")