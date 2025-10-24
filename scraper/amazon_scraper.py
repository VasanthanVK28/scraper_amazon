import asyncio
import re
from playwright.async_api import async_playwright
from config.settings import SEARCH_URL, HEADLESS
from database.mongo_handler import upsert_product

#query=>search keyword,collection_name=>mongodb collection name ,max_pages=>number of pages to scrape
async def scrape_amazon(query="mobile", collection_name="products", max_pages=10):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

    #scraping timing logic

        url = SEARCH_URL.format(query=query)
        print(f"🔎 Navigating to {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        #pagination logic
        
        page_num = 1
        while True:
            print(f"\n📄 Scraping page {page_num} for {query}...")

            await page.wait_for_selector("div.s-main-slot div[data-asin]")
            products = await page.query_selector_all("div.s-main-slot div[data-asin]")

    #product extraction logic
    # safely handle parsing errors per product without stopping the entire scrape.
            printed_one = False 
            for product in products:
                try:
                    asin = await product.get_attribute("data-asin")
                    if not asin:
                        continue

                    # Extract Title
                    title_el = (
                        await product.query_selector("h2 a span")
                        or await product.query_selector("h2 a")
                        or await product.query_selector("h2")
                    )
                    title = await title_el.inner_text() if title_el else None

                    # Extract Price . If there is no price , it will be None
                    price = None
                    price_whole = await product.query_selector("span.a-price-whole")
                    if price_whole:
                        price_text = await price_whole.inner_text()
                        #tries to select the fraction part of the price
                        price_fraction = await product.query_selector("span.a-price-fraction")
                        if price_fraction:
                            price_text += "." + await price_fraction.inner_text()
                            
                            # Combine whole and fraction parts
                        try:
                            price = float(price_text.replace(",", ""))
                        except ValueError:
                            pass

                    # Extract Rating , If there is no rating , it will be None
                    rating = None
                    #- Selects the element that typically contains text like "4.3 out of 5 stars".

                    rating_el = await product.query_selector("span.a-icon-alt")
                    #- converts it to float for the numeric rating.

                    if rating_el:
                        try:
                            rating_text = await rating_el.inner_text()
                            rating = float((await rating_el.inner_text()).split()[0])
                        except ValueError:
                            pass    

                    # Extract Reviews

                    reviews = 0
                    #These are the different places where reviews count might be located.
                    review_selectors = [
                        "span.s-underline-text",
                        "span.a-size-base.s-underline-text",
                        "a.a-link-normal.s-underline-text.s-link-style",
                    ]
                    # Iterate through possible selectors to find reviews count
                    # stops at the first match  
                    #\d+ to capture the numeric part of the reviews text.
                    for selector in review_selectors:
                        reviews_el = await product.query_selector(selector)
                        if reviews_el:
                            reviews_text = (await reviews_el.inner_text()).strip()
                            #print(f"📝 Raw reviews string from DOM: {reviews_text}")

                                    # Match numbers with commas (e.g., 3,123 or 12,345,678)
                            match = re.search(r"\b[\d,]+\b", reviews_text)
                            if match:
                                reviews = int(match.group(0).replace(",", ""))
                                break


                    # Image
                    image_url = None
                    image_el = await product.query_selector("img.s-image")
                    if image_el:
                        image_url = await image_el.get_attribute("src")

                    # Product URL
                
                    product_url = None
                    #/dp/ or /gp/ links typically lead to product detail pages.
                    #dp => detail page - - Every Amazon product has a canonical detail page, gp => general product page

                    product_url_el = await product.query_selector("a[href*='/dp/'], a[href*='/gp/']")
                    if product_url_el:
                        href = await product_url_el.get_attribute("href")
                        if href:
                            # Clean URL: strip query params, prepend domain if relative
                            if href.startswith("http"):
                                product_url = href.split("?")[0]
                            else:
                                product_url = "https://www.amazon.in" + href.split("?")[0]
                    # Skip if essential data is missing

                    if not (title and price):
                        continue

                    product_doc = {
                        "asin": asin,
                        "title": title,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "image_url": image_url,
                        "product_url": product_url,
                    }

                    # ✅ Debug print in terminal
                    if not printed_one:

                        print("\n🛒 Scraped Product:")
                        print(f"   ASIN: {asin}")
                        print(f"   Title: {title}")
                        print(f"   Price: ₹{price}")
                        print(f"   Rating: {rating}")
                        print(f"   Reviews: {reviews}")
                        print(f"   Image: {image_url}")
                        print(f"   URL: {product_url}")
                        printed_one = True



                    # Save to MongoDB
                    upsert_product(product_doc, collection_name)

                except Exception as e:
                    print(f"⚠️ Skipped one product due to error: {e}")

                    return

            # Pagination
            next_button = await page.query_selector("a.s-pagination-next")
            if next_button and await next_button.is_enabled():
                await next_button.click()
                await page.wait_for_selector("div.s-main-slot div[data-asin]", timeout=60000)
                page_num += 1
                if page_num > max_pages:
                    break
            else:
                break
            #print(f"✅ Completed scraping for query '{query}' in collection '{collection_name}'")

        await browser.close()