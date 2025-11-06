# scheduler_manager.py
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from scraper.amazon_scraper import scrape_amazon
from config.settings import CATEGORIES

scheduler = BackgroundScheduler()
scheduler.start()  # Start in background

# --- Async scraping task ---
async def scrape_all():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scraping...")
    for query, collection in CATEGORIES.items():
        await scrape_amazon(query, collection_name=collection, max_pages=5)
        print(f"✓ Finished scraping {query}")
    print("✅ All scraping tasks completed!\n")

def run_scraper_job():
    asyncio.run(scrape_all())

# --- Scheduler functions ---
def schedule_job(job_id, frequency, time=None, day_of_week=None, interval_hours=None):
    # Remove existing job if it exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if frequency == "daily":
        hour, minute = map(int, time.split(":"))
        scheduler.add_job(run_scraper_job, CronTrigger(hour=hour, minute=minute), id=job_id)
    elif frequency == "weekly":
        hour, minute = map(int, time.split(":"))
        scheduler.add_job(run_scraper_job, CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute), id=job_id)
    elif frequency == "hourly":
        scheduler.add_job(run_scraper_job, IntervalTrigger(hours=interval_hours), id=job_id)
    
    print(f"✅ Job '{job_id}' scheduled successfully!")

def list_jobs():
    jobs = scheduler.get_jobs()
    return [{"id": j.id, "next_run_time": str(j.next_run_time)} for j in jobs]

def remove_job(job_id):
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"❌ Job '{job_id}' removed")
        return True
    return False
