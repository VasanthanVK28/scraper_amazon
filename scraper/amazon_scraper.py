# scraper/amazon_scraper.py

import asyncio
from playwright.async_api import async_playwright
import datetime
from config.settings import SEARCH_URL, HEADLESS
from database.mongo_handler import upsert_product


async def scrape_amazon(query="mobile"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        url = SEARCH_URL.format(query=query)
        print(f"🔎 Navigating to {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")

        # Wait for product grid
        await page.wait_for_selector("div.s-main-slot div[data-asin]")
        products = await page.query_selector_all("div.s-main-slot div[data-asin]")

        for product in products:
            try:
                asin = await product.get_attribute("data-asin")
                if not asin:
                    continue

                # Title
                # Try multiple selectors for title
                title = None

# 1. Most common: span inside h2 > a
                title_el = await product.query_selector("h2 a span")
                if title_el:
                    title = await title_el.inner_text()
# 2. Fallback: h2 > a directly (sometimes text is here)
                if not title:
                    title_el = await product.query_selector("h2 a")
                    if title_el:
                        title = await title_el.inner_text()
# 3. Last fallback: h2 itself
                if not title:
                    title_el = await product.query_selector("h2")
                    if title_el:
                        title = await title_el.inner_text()

                # Price (whole + fraction)
                price_whole = await product.query_selector("span.a-price-whole")
                price_fraction = await product.query_selector("span.a-price-fraction")
                if price_whole:
                    price_text = await price_whole.inner_text()
                    if price_fraction:
                        price_text += "." + await price_fraction.inner_text()
                    try:
                        price = float(price_text.replace(",", ""))
                    except:
                        price = None
                else:
                    price = None

                # Rating
                rating_el = await product.query_selector("span.a-icon-alt")
                rating = None
                if rating_el:
                    try:
                        rating = float((await rating_el.inner_text()).split()[0])
                    except:
                        rating = None

                # Reviews count
                reviews_el = await product.query_selector("span.s-underline-text")
                try:
                    reviews = int((await reviews_el.inner_text()).replace(",", "")) if reviews_el else None
                except:
                    reviews = None

                # Image
                image_el = await product.query_selector("img.s-image")
                image_url = await image_el.get_attribute("src") if image_el else None

                # Product URL
                product_url_el = await product.query_selector("h2 a")
                product_url = (
                    "https://www.amazon.in" + (await product_url_el.get_attribute("href"))
                    if product_url_el
                    else None
                )

                # Build document
                product_doc = {
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "reviews": reviews,
                    "image_url": image_url,
                    "product_url": product_url,
                    "last_updated": datetime.datetime.utcnow(),
                }

                # Debug print
                print(
                    f"Title: {title}, Price: {price}, Rating: {rating}, "
                    f"Reviews: {reviews}, Image: {image_url}, URL: {product_url}"
                )

                # Store in MongoDB
                upsert_product(product_doc)
                print(f"✅ Stored: {title} | ASIN: {asin}")

            except Exception as e:
                print(f"⚠️ Skipped one product due to error: {e}")

        await browser.close()