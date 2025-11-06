# main.py
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from scraper.amazon_scraper import scrape_amazon
from config.settings import CATEGORIES

app = FastAPI()

# Allow frontend (React) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()
scheduler.start()

class SchedulePayload(BaseModel):
    scrapeFrequency: str  # hourly / daily / weekly
    scrapeTime: str = "03:00"
    scrapeDay: str = "sun"

# Run scraper for all categories
async def scrape_all():
    print(f"[{datetime.now()}] 🔍 Starting scraping job...")
    for query, collection in CATEGORIES.items():
        print(f"→ Scraping '{query}' into '{collection}' collection...")
        await scrape_amazon(query, collection_name=collection, max_pages=5)
        print(f"✓ Finished scraping '{query}'")
    print(f"[{datetime.now()}] ✅ Scraping job finished.\n")

# Sync wrapper for APScheduler
def start_scraper_job():
    asyncio.run(scrape_all())

@app.post("/api/schedule-scrape")
def schedule_scrape(payload: SchedulePayload):
    try:
        scheduler.remove_all_jobs()
        hour, minute = map(int, payload.scrapeTime.split(":"))

        if payload.scrapeFrequency == "hourly":
            scheduler.add_job(start_scraper_job, trigger=IntervalTrigger(hours=1), id="scrape_job")
            freq = "hourly"
        elif payload.scrapeFrequency == "daily":
            scheduler.add_job(start_scraper_job, trigger=CronTrigger(hour=hour, minute=minute), id="scrape_job")
            freq = f"daily at {payload.scrapeTime}"
        elif payload.scrapeFrequency == "weekly":
            scheduler.add_job(
                start_scraper_job,
                trigger=CronTrigger(day_of_week=payload.scrapeDay, hour=hour, minute=minute),
                id="scrape_job"
            )
            freq = f"weekly on {payload.scrapeDay} at {payload.scrapeTime}"
        else:
            raise HTTPException(status_code=400, detail="Invalid frequency")

        print(f"✅ Scraping job scheduled: {freq}")
        return {"status": "success", "message": f"Scraping scheduled {freq}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schedule-status")
def get_schedule_status():
    """Check what’s currently scheduled."""
    jobs = scheduler.get_jobs()
    if not jobs:
        return {"scheduled": False, "message": "No active scraping job"}
    job = jobs[0]
    return {
        "scheduled": True,
        "next_run": str(job.next_run_time),
        "trigger": str(job.trigger),
    }
