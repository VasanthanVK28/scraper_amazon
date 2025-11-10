import asyncio
import re
from playwright.async_api import async_playwright
from config.settings import SEARCH_URL, HEADLESS
from database.mongo_handler import upsert_product, ensure_indexes


# ---------- Helper: classify tags ----------
def classify_tags(query: str, title: str | None) -> list[str]:
    q = (query or "").lower()
    t = (title or "").lower()
    if "mobile" in q or "phone" in t:
        return ["mobile", "electronics"]
    if "laptop" in q or "laptop" in t:
        return ["laptop", "electronics"]
    if "toy" in q or "toy" in t:
        return ["toys", "kids"]
    if "sofa" in q or "couch" in t:
        return ["sofa", "furniture"]
    if "shirt" in q or "tshirt" in t or "top" in t:
        return ["shirt", "fashion"]
    return [q]


# ---------- Core Scraper ----------
async def scrape_amazon(query="mobile", collection_name="products", max_products=5):
    """Scrape Amazon search results for a given query and save products in MongoDB."""
    ensure_indexes(collection_name)  # ensure unique index on ASIN

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        url = SEARCH_URL.format(query=query)

        print(f"🔎 Navigating to {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # 🧠 Try multiple selectors (Amazon layout changes often)
        selectors = [
            "div.s-main-slot div[data-component-type='s-search-result']",
            "div[data-asin][data-component-type='s-search-result']",
        ]

        found_selector = None
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=30000)
                found_selector = selector
                break
            except Exception:
                continue

        if not found_selector:
            # 🧩 Take a screenshot to debug
            await page.screenshot(path=f"debug_{query}.png")
            html = await page.content()
            if "robot" in html.lower() or "captcha" in html.lower():
                print("🚫 Amazon blocked the scraper (CAPTCHA or Bot detection). Try rotating IP/User-Agent.")
            raise Exception("Product list selector not found on the page.")

        products = await page.query_selector_all(found_selector)
        print(f"📦 Found {len(products)} products for '{query}'")

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
                    except ValueError:
                        pass

                # RATING
                rating = None
                rating_el = await product.query_selector("span.a-icon-alt")
                if rating_el:
                    rating_text = await rating_el.inner_text()
                    m = re.search(r"[\d.]+", rating_text)
                    if m:
                        rating = float(m.group(0))

                # REVIEWS
                reviews = 0
                review_el = await product.query_selector("span.a-size-base.s-underline-text")
                if review_el:
                    review_text = await review_el.inner_text()
                    m = re.search(r"[\d,]+", review_text)
                    if m:
                        reviews = int(m.group(0).replace(",", ""))

                # IMAGE
                img_el = await product.query_selector("img.s-image")
                image_url = await img_el.get_attribute("src") if img_el else None

                # PRODUCT LINK
                link_el = await product.query_selector("h2 a")
                product_url = None
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            href = "https://www.amazon.in" + href.split("?")[0]
                        product_url = href

                # BRAND + TAGS
                brand = title.split()[0] if title else "Unknown"
                tags = classify_tags(query, title)

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
                    "query": query,
                }

                upsert_product(product_doc, collection_name)
                scraped_count += 1
                print(f"🛒 [{scraped_count}/{max_products}] {title[:80]} | ₹{price if price else 'N/A'}")

            except Exception as e:
                print(f"⚠️ Error parsing product: {e}")

        await browser.close()
        print(f"✅ Completed scraping {scraped_count} products for '{query}'")
        return scraped_count


# ---------- Run standalone ----------
if __name__ == "__main__":
    asyncio.run(scrape_amazon("mobiles"))
