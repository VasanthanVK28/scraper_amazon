import asyncio
import random
import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from bson import ObjectId
from config.settings import MONGO_URI, DB_NAME
from scraper.amazon_scraper import scrape_amazon
from utils.email_notifier import send_failure_email

# ---------------- MongoDB setup ----------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
schedule_collection = db["scrape_schedules"]

# ---------------- Helper: Update schedule status ----------------
def set_schedule_status(schedule_id, is_running=False, status=None, last_run=None):
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

    # ---------------- FIX: Convert JSON string → dict ----------------
    raw_categories = schedule.get("categories")

    if isinstance(raw_categories, str):  # when stored as JSON string
        try:
            categories = json.loads(raw_categories)
        except:
            categories = {}
    elif isinstance(raw_categories, dict):  # when already dict
        categories = raw_categories
    else:
        categories = {}

    # ---------------------------------------------------------------
    # If categories empty → scrape all default categories
    # ---------------------------------------------------------------
    ALL_CATEGORIES = {
        "mobiles": "mobiles_collection",
        "laptops": "laptops_collection",
        "shirts": "shirts_collection",
        "toys": "toys_collection",
        "sofas": "sofas_collection",
    }

    if not categories:
        print("⚠️ No admin-selected categories found. Scraping ALL categories.")
        categories = ALL_CATEGORIES
    else:
        print("✅ Admin-selected categories:", categories)

    # ---------------- Debounce: Limit frequent runs ----------------
    if last_run:
        time_since_last = (datetime.now() - last_run).total_seconds()
        if time_since_last < 10:
            wait_time = random.randint(10, 20)
            print(f"⏳ Waiting {wait_time}s due to rate limit")
            await asyncio.sleep(wait_time)

    print(f"\n⏱️ Starting scrape for schedule '{frequency}'...")
    set_schedule_status(schedule_id, is_running=True, status="active")

    try:
        await asyncio.sleep(random.randint(5, 10))  # initial delay

        # ---------------- SCRAPE ONLY SELECTED CATEGORIES ----------------
        for query, collection_name in categories.items():
            print(f"🔹 Scraping 5 items for category: {query}")
            scraped = await scrape_amazon(
                query=query,
                collection_name=collection_name,
                max_products=5
            )
            print(f"✅ Scraped {scraped} items for '{collection_name}'")

        now = datetime.now()
        set_schedule_status(schedule_id, is_running=False, status="complete", last_run=now)
        print(f"✔️ Scrape complete | Last run: {now.strftime('%I:%M %p')}")

    except Exception as e:
        set_schedule_status(schedule_id, is_running=False, status="failed")
        print(f"❌ Scrape failed: {e}")
        await send_failure_email(str(e), frequency)


# ---------------- Check Schedules ----------------
async def check_schedules():
    now = datetime.now()
    current_day = now.strftime("%a").lower()

    active_schedules = list(schedule_collection.find({"is_running": False}))

    for schedule in active_schedules:
        frequency = schedule.get("frequency")
        schedule_time = schedule.get("time")
        schedule_day = schedule.get("day")
        last_run = schedule.get("last_run")

        run = False

        # Hourly
        if frequency == "hourly":
            run = True

        # Daily
        elif frequency == "daily" and schedule_time:
            hh, mm = schedule_time.split(":")
            if now.hour == int(hh) and now.minute == int(mm):
                if not last_run or last_run.date() != now.date():
                    run = True

        # Weekly
        elif frequency == "weekly" and schedule_day and schedule_time:
            hh, mm = schedule_time.split(":")
            if schedule_day.lower() == current_day:
                if now.hour == int(hh) and now.minute == int(mm):
                    if not last_run or last_run.date() != now.date():
                        run = True

        if run:
            asyncio.create_task(run_scrape(schedule))


# ---------------- Main Entry ----------------
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_schedules, "interval", minutes=1, coalesce=True)
    scheduler.start()

    print("🟢 Scheduler running every 1 minute...")

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
