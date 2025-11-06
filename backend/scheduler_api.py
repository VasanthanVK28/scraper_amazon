# backend/scheduler_api.py
from fastapi import FastAPI, HTTPException, Depends
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import asyncio
from scraper.amazon_scraper import scrape_amazon
from config.settings import CATEGORIES

app = FastAPI()
scheduler = BackgroundScheduler()
scheduler.start()


async def scrape_all():
    print(f"[{datetime.now()}] Starting scheduled scrape...")
    for query, collection in CATEGORIES.items():
        await scrape_amazon(query, collection_name=collection, max_pages=5)
    print("All scraping tasks completed!")

def start_scraper_job():
    asyncio.run(scrape_all())

# Admin dependency (example)
def admin_only():
    # Here, check the logged-in user role
    # Raise HTTPException(status_code=403) if not admin
    return True

# 🔹 Add job
@app.post("/schedule-job/")
def add_job(frequency: str, hour: int = 0, minute: int = 0, day_of_week: str = None, admin: bool = Depends(admin_only)):
    job_id = f"scrape_{frequency}"
    if frequency == "daily":
        scheduler.add_job(start_scraper_job, "cron", hour=hour, minute=minute, id=job_id)
    elif frequency == "hourly":
        scheduler.add_job(start_scraper_job, "interval", hours=1, id=job_id)
    elif frequency == "weekly":
        if not day_of_week:
            raise HTTPException(status_code=400, detail="day_of_week is required for weekly schedule")
        scheduler.add_job(start_scraper_job, "cron", day_of_week=day_of_week, hour=hour, minute=minute, id=job_id)
    return {"status": "success", "job_id": job_id}

# 🔹 List jobs
@app.get("/list-jobs/")
def list_jobs(admin: bool = Depends(admin_only)):
    jobs = scheduler.get_jobs()
    return [{"id": job.id, "next_run": str(job.next_run_time)} for job in jobs]

# 🔹 Remove job
@app.delete("/remove-job/{job_id}")
def remove_job(job_id: str, admin: bool = Depends(admin_only)):
    scheduler.remove_job(job_id)
    return {"status": "removed", "job_id": job_id}
