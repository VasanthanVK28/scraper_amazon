import asyncio
import re
from playwright.async_api import async_playwright
from config.settings import SEARCH_URL, HEADLESS
from database.mongo_handler import upsert_product



# ================== TAG CLASSIFIER ==================
def classify_tags(query: str, title: str | None) -> list[str]:
    """Return tags based on query and title content."""
    query = (query or "").lower()
    title = (title or "").lower()

    # Explicit mapping by query keyword
    tag_map = {
        "mobile": ["mobile", "electronics", "phone"],
        "laptop": ["laptop", "electronics", "computer"],
        "sofa": ["sofa", "furniture", "home"],
        "shirt": ["shirt", "fashion", "clothing"],
        "toys": ["toys", "kids", "entertainment"],
        "toy": ["toys", "kids", "entertainment"],
    }
    if query in tag_map:
        return tag_map[query]

    # Title-based fallback
    if any(word in title for word in ["sofa", "couch", "settee", "divan"]):
        return ["sofa", "furniture", "home"]
    if any(word in title for word in ["shirt", "tshirt", "tee", "kurta", "blouse", "top"]):
        return ["shirt", "fashion", "clothing"]
    if any(word in title for word in ["toy", "truck", "doll", "lego", "car", "puzzle"]):
        return ["toys", "kids", "entertainment"]
    if any(word in title for word in ["mobile", "phone", "smartphone", "redmi", "samsung"]):
        return ["mobile", "electronics", "phone"]
    if any(word in title for word in ["laptop", "macbook", "notebook", "hp", "dell"]):
        return ["laptop", "electronics", "computer"]

    # Default fallback
    return [query]


# ================== MAIN SCRAPER ==================
async def scrape_amazon(query="mobile", collection_name="products", max_pages=10):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        url = SEARCH_URL.format(query=query)
        print(f"🔎 Navigating to {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")

        page_num = 1
        while True:
            print(f"\n📄 Scraping page {page_num} for {query}...")
            await page.wait_for_selector("div.s-main-slot div[data-asin]")
            products = await page.query_selector_all("div.s-main-slot div[data-asin]")

            printed_one = False
            for product in products:
                try:
                    asin = await product.get_attribute("data-asin")
                    if not asin:
                        continue

                    # --- Title ---
                    title_el = (
                        await product.query_selector("h2 a span")
                        or await product.query_selector("h2 a")
                        or await product.query_selector("h2")
                    )
                    title = await title_el.inner_text() if title_el else None

                    # --- Price ---
                    price = None
                    price_whole = await product.query_selector("span.a-price-whole")
                    if price_whole:
                        price_text = await price_whole.inner_text()
                        price_fraction = await product.query_selector("span.a-price-fraction")
                        if price_fraction:
                            price_text += "." + await price_fraction.inner_text()
                        try:
                            price = float(price_text.replace(",", ""))
                        except ValueError:
                            pass

                    # --- Rating ---
                    rating = None
                    rating_el = await product.query_selector("span.a-icon-alt")
                    if rating_el:
                        try:
                            rating = float((await rating_el.inner_text()).split()[0])
                        except ValueError:
                            pass

                    # --- Reviews ---
                    reviews = 0
                    review_selectors = [
                        "span.s-underline-text",
                        "span.a-size-base.s-underline-text",
                        "a.a-link-normal.s-underline-text.s-link-style",
                    ]
                    for selector in review_selectors:
                        reviews_el = await product.query_selector(selector)
                        if reviews_el:
                            reviews_text = (await reviews_el.inner_text()).strip()
                            match = re.search(r"\b[\d,]+\b", reviews_text)
                            if match:
                                reviews = int(match.group(0).replace(",", ""))
                                break

                    # --- Image ---
                    image_url = None
                    image_el = await product.query_selector("img.s-image")
                    if image_el:
                        image_url = await image_el.get_attribute("src")

                       # --- Brand ---
            
                    brand = None
                    try:
                         
                        # ✅ 1. Try explicit brand heading (appears above title)
                        brand_el = await product.query_selector("h5.s-line-clamp-1 span, h5.s-line-clamp-1")
                        if brand_el:
                            text = (await brand_el.inner_text()).strip()
                            if text and not any(bad in text.lower() for bad in ["bought", "deal", "offer", "price", "mrp","bought in past month","amazon choice","sponsored","deal","limited","%","off","offer"]):
                                brand = text

                                # ✅ 2. If still missing, extract from title start (e.g., "Samsung Galaxy S24 Ultra")

                        if not brand and title:
                            possible = title.strip().split()[0]  # take first word
                            if possible.isalpha() and len(possible) >= 2:
                                brand = possible

                    except Exception as e:
                        print(f"⚠️ Brand extraction failed for ASIN={asin}: {e}")

                        # ✅ Default fallback

                    if not brand:
                        brand = "Unknown"




                    # --- Product URL ---
                    product_url = None
                    product_url_el = await product.query_selector("a[href*='/dp/'], a[href*='/gp/']")
                    if product_url_el:
                        href = await product_url_el.get_attribute("href")
                        if href:
                            if href.startswith("http"):
                                product_url = href.split("?")[0]
                            else:
                                product_url = "https://www.amazon.in" + href.split("?")[0]

                    if not (title and price):
                        continue

                    # --- Tags (updated) ---
                    tags = classify_tags(query, title)

                    # --- Product Document ---
                    product_doc = {
                        "asin": asin,
                        "title": title,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "image_url": image_url,
                        "product_url": product_url,
                        "tags": tags,
                        "brand": brand,
                    }

                    if not printed_one:
                        print("\n🛒 Scraped Product:")
                        print(f"   ASIN: {asin}")
                        print(f"   Title: {title}")
                        print(f"   Price: ₹{price}")
                        print(f"   Rating: {rating}")
                        print(f"   Reviews: {reviews}")
                        print(f"   Image: {image_url}")
                        print(f"   URL: {product_url}")
                        print(f"   Tags: {product_doc['tags']}")
                        print(f"   Brand: {brand}")

                        printed_one = True

                    # Save to MongoDB
                    upsert_product(product_doc, collection_name)

                except Exception as e:
                    print(f"⚠️ Skipped one product due to error: {e}")
                    continue

            # --- Pagination ---
            next_button = await page.query_selector("a.s-pagination-next")
            if next_button and await next_button.is_enabled():
                await next_button.click()
                await page.wait_for_selector("div.s-main-slot div[data-asin]", timeout=60000)
                page_num += 1
                if page_num > max_pages:
                    break
            else:
                break
                
        await browser.close()
    print(f"\n✅ Completed scraping for '{query}' into collection '{collection_name}'.")
# ================== ENTRY POINT ==================
if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "mobile"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    # Automatically choose collection name based on query
    collection_map = {
        "mobile": "mobiles",
        "mobiles": "mobiles",
        "laptop": "laptops",
        "laptops": "laptops",
        "toy": "toys",
        "toys": "toys",
        "shirt": "shirts",
        "shirts": "shirts",
        "sofa": "sofas",
        "sofas": "sofas",
    }
    collection_name = collection_map.get(query.lower(), "products")

    import asyncio
    asyncio.run(scrape_amazon(query=query, collection_name=collection_name, max_pages=pages))
