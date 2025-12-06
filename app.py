# app.py
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from amazon import scrape_amazon  # your existing Playwright scraper

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with your React frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Request Schema ----------------
class ScrapeRequest(BaseModel):
    category: str
    max_products: int = 5

# ---------------- Endpoint to trigger scraping ----------------
@app.post("/scrape-products")
async def scrape_products(req: ScrapeRequest):
    try:
        # Run your existing Playwright scraper
        scraped = await scrape_amazon(category=req.category, max_products=req.max_products)
        return {"status": "success", "scraped": scraped, "category": req.category}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------- Run server ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
