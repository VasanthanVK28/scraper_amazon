# Filename: real_time_amazon.py

import asyncio
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from database.mongo_handler import upsert_product, ensure_indexes

# ---------- Helper: classify tags ----------
def classify_tags(category: str, title: str) -> list:
    """
    Always returns the admin-entered category as tag.
    """
    return [category.lower()]

# ---------------- Scraper Function ----------------
async def scrape_amazon(category="mobile", collection_name="scraped_products", max_products=5):
    """
    Scrape Amazon search results for a given category and save products in MongoDB.
    """
    ensure_indexes(collection_name)  # ensure unique index on ASIN

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        url = f"https://www.amazon.in/s?k={category}"

        print(f"[{datetime.now()}] 🔎 Scraping category: {category}")
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(3000)

        # Selector for search result items
        selector = "div.s-main-slot div[data-component-type='s-search-result']"
        try:
            await page.wait_for_selector(selector, timeout=10000)
        except:
            await browser.close()
            print("Selector not found. Amazon might be blocking requests.")
            return 0

        products = await page.query_selector_all(selector)
        scraped_count = 0

        for product in products:
            if scraped_count >= max_products:
                break
            try:
                asin = await product.get_attribute("data-asin")
                if not asin:
                    continue

                # TITLE
                title_el = await product.query_selector("h2 span")
                title = (await title_el.inner_text()).strip() if title_el else None
                if not title:
                    continue

                # PRICE
                price = None
                price_el = await product.query_selector("span.a-price > span.a-offscreen")
                if price_el:
                    price_text = (await price_el.inner_text()).replace("₹", "").replace(",", "").strip()
                    try:
                        price = float(price_text)
                    except:
                        price = None

                # BRAND
                brand = "Unknown"
                brand_el = await product.query_selector(
                    "span.a-size-base-plus.a-color-secondary, span.a-text-normal"
                )
                if brand_el:
                    brand_text = (await brand_el.inner_text()).strip()
                    if brand_text:
                        brand = brand_text
                else:
                    brand = title.split()[0]

                # RATING
                rating = 0.0
                rating_selectors = [
                    "span.a-icon-alt",
                    
                
                ]
                for sel in rating_selectors:
                    try:
                        rating_el = await product.query_selector(sel)
                        if rating_el:
                            text = await rating_el.inner_text()
                            m = re.search(r"[\d.]+", text)
                            if m:
                                rating = float(m.group(0))
                                break
                    except:
                        continue

                # REVIEWS
                reviews = 0
                review_selectors = [
                    "span[aria-label][class*='a-size-base']",
                    "span.a-size-small span[aria-label]",
                    "span[data-hook='total-review-count']"
                ]
                for sel in review_selectors:
                    try:
                        review_el = await product.query_selector(sel)
                        if review_el:
                            text = await review_el.inner_text()
                            m = re.search(r"[\d,]+", text)
                            if m:
                                reviews = int(m.group(0).replace(",", ""))
                                break
                    except:
                        continue

                # IMAGE
                image_el = await product.query_selector("img.s-image")
                image_url = await image_el.get_attribute("src") if image_el else None

                # PRODUCT URL
                link_el = await product.query_selector("h2 a")
                product_url = None
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        product_url = "https://www.amazon.in" + href.split("?")[0]

                # TAGS
                tags = classify_tags(category, title)

                # Document
                product_doc = {
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "brand": brand,
                    "rating": rating,
                    "reviews": reviews,
                    "image_url": image_url,
                    "product_url": product_url,
                    "category": category,
                    "tags": tags,
                    "scraped_at": datetime.now()
                }

                # Upsert into MongoDB
                upsert_product(product_doc, collection_name)
                scraped_count += 1
                print(f"🛒 [{scraped_count}/{max_products}] {title[:60]} | ₹{price if price else 'N/A'} | {brand} | ⭐{rating} | Reviews: {reviews}")

                await asyncio.sleep(random.uniform(2, 4))  # throttle requests

            except Exception as e:
                print(f"⚠️ Error parsing product: {e}")

        await browser.close()
        print(f"[{datetime.now()}] ✅ Completed scraping {scraped_count} products for category '{category}'\n")
        return scraped_count

# ---------------- Admin Menu ----------------
async def admin_menu():
    print("\n=== Amazon Real-Time Category Scraper ===\n")
    while True:
        category = input("Enter category to scrape (or 'exit' to quit): ").strip()
        if category.lower() == "exit":
            print("Exiting scraper.")
            break
        if category:
            ensure_indexes("scraped_products")
            scraped_count = await scrape_amazon(
                category=category,
                collection_name="scraped_products",
                max_products=5
            )
            print(f"✅ Scraped {scraped_count} products for category '{category}'\n")

# ---------------- Main ----------------
if __name__ == "__main__":
    asyncio.run(admin_menu())
