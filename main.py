# main.py

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from bson import ObjectId
from config.settings import MONGO_URI, DB_NAME, CATEGORIES
from scraper.amazon_scraper import scrape_amazon
from utils.email_notifier import send_failure_email  # ✅ NEW IMPORT

# ---------------- MongoDB setup ----------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
schedule_collection = db["scrape_schedules"]

# ---------------- Helper: Update schedule status ----------------
def set_schedule_status(schedule_id, is_running=False, status=None):
    """Update the running state and status of a scraping schedule."""
    update_query = {"is_running": is_running}
    if status:
        update_query["status"] = status
    schedule_collection.update_one({"_id": ObjectId(schedule_id)}, {"$set": update_query})

# ---------------- Run Scraper ----------------
async def run_scrape(schedule):
    schedule_id = schedule["_id"]
    frequency = schedule["frequency"]

    print(f"\n⏱️ Running scrape for schedule '{frequency}'...")
    set_schedule_status(schedule_id, is_running=True, status="active")

    try:
        for query, collection_name in CATEGORIES.items():
            print(f"🔹 Scraping up to 5 products for category: {query}")
            scraped_count = await scrape_amazon(query=query, collection_name=collection_name, max_products=5)
            print(f"✅ Scraped {scraped_count} products for '{collection_name}'")

        set_schedule_status(schedule_id, is_running=False, status="complete")
        print(f"✅ Completed scrape for schedule '{frequency}'")

    except Exception as e:
        set_schedule_status(schedule_id, is_running=False, status="failed")
        print(f"❌ Failed scrape for schedule '{frequency}': {e}")

        # ✅ Send failure email
        await send_failure_email(str(e), frequency)

# ---------------- Check Schedules ----------------
async def check_schedules():
    """Check for active scraping schedules and trigger jobs."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_day = now.strftime("%a").lower()

    active_schedules = list(schedule_collection.find({"is_running": False}))
    for schedule in active_schedules:
        freq = schedule.get("frequency")
        sched_time = schedule.get("time")
        sched_day = schedule.get("day")

        run = False
        if freq == "hourly":
            run = True
        elif freq == "daily" and sched_time == current_time:
            run = True
        elif (
            freq == "weekly"
            and sched_day
            and sched_time
            and sched_day.lower() == current_day
            and sched_time == current_time
        ):
            run = True

        if run:
            asyncio.create_task(run_scrape(schedule))

# ---------------- Main Entry ----------------
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_schedules, "interval", minutes=1, coalesce=True)
    scheduler.start()

    print("🟢 Scheduler running (checks every 1 minute)...")

    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
