import asyncio
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from bson import ObjectId
from config.settings import MONGO_URI, DB_NAME, CATEGORIES
from scraper.amazon_scraper import scrape_amazon
from utils.email_notifier import send_failure_email

# ---------------- MongoDB setup ----------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
schedule_collection = db["scrape_schedules"]

# ---------------- Helper: Update schedule status ----------------
def set_schedule_status(schedule_id, is_running=False, status=None, last_run=None):
    """Update the running state, status, and last_run of a scraping schedule."""
    update_query = {"is_running": is_running, "updated_at": datetime.now()}
    if status:
        update_query["status"] = status
    if last_run:
        update_query["last_run"] = last_run
    schedule_collection.update_one({"_id": ObjectId(schedule_id)}, {"$set": update_query})

# ---------------- Run Scraper ----------------
async def run_scrape(schedule):
    schedule_id = schedule["_id"]
    frequency = schedule.get("frequency")
    last_run = schedule.get("last_run")

    if last_run:
        print(f"🕒 Last run for this schedule: {last_run.strftime('%I:%M %p')}")
        # Respect at least 10–20 seconds delay from last run
        time_since_last = (datetime.now() - last_run).total_seconds()
        if time_since_last < 10:
            wait_time = random.randint(10, 20)
            print(f"⏳ Waiting {wait_time} seconds to respect rate limits...")
            await asyncio.sleep(wait_time)

    print(f"\n⏱️ Running scrape for schedule '{frequency}'...")
    set_schedule_status(schedule_id, is_running=True, status="active")

    try:
        # Random delay before starting scrape
        delay_seconds = random.randint(10, 20)
        print(f"⏳ Initial delay: {delay_seconds} seconds to avoid detection")
        await asyncio.sleep(delay_seconds)

        for query, collection_name in CATEGORIES.items():
            print(f"🔹 Scraping up to 5 products for category: {query}")
            scraped_count = await scrape_amazon(query=query, collection_name=collection_name, max_products=5)
            print(f"✅ Scraped {scraped_count} products for '{collection_name}'")

        # Mark schedule as complete and update last_run
        now = datetime.now()
        set_schedule_status(schedule_id, is_running=False, status="complete", last_run=now)
        print(f"✅ Completed scrape for schedule '{frequency}' | Last run updated to {now.strftime('%I:%M %p')}")

    except Exception as e:
        set_schedule_status(schedule_id, is_running=False, status="failed")
        print(f"❌ Failed scrape for schedule '{frequency}': {e}")
        await send_failure_email(str(e), frequency)

# ---------------- Check Schedules ----------------
async def check_schedules():
    """Check for active scraping schedules and trigger jobs."""
    now = datetime.now()
    current_day = now.strftime("%a").lower()

    active_schedules = list(schedule_collection.find({"is_running": False}))
    for schedule in active_schedules:
        freq = schedule.get("frequency")
        sched_time = schedule.get("time")  # expected format "HH:MM"
        sched_day = schedule.get("day")
        last_run = schedule.get("last_run")

        run = False

        if freq == "hourly":
            run = True

        elif freq == "daily" and sched_time:
            hh_mm = sched_time.split(":")
            target_hour = int(hh_mm[0])
            target_minute = int(hh_mm[1])

            # Run if hour/minute match and not already run today
            if now.hour == target_hour and now.minute == target_minute:
                if not last_run or last_run.date() != now.date():
                    run = True

        elif freq == "weekly" and sched_day and sched_time:
            hh_mm = sched_time.split(":")
            target_hour = int(hh_mm[0])
            target_minute = int(hh_mm[1])
            if sched_day.lower() == current_day and now.hour == target_hour and now.minute == target_minute:
                if not last_run or last_run.date() != now.date():
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
