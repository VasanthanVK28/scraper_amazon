import asyncio
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from scraper.amazon_scraper import scrape_amazon  # your async scrape function
from config.settings import CATEGORIES  # dictionary of queries and collections

# Initialize the scheduler
scheduler = BlockingScheduler()

async def scrape_all():
    """
    Run the Amazon scraper for all categories asynchronously.
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled scrape...\n")

    for query, collection in CATEGORIES.items():
        print(f"→ Scraping '{query}' into '{collection}' collection")
        try:
            await scrape_amazon(query, collection_name=collection, max_pages=5)
            print(f"✓ Finished scraping '{query}'\n")
        except Exception as e:
            print(f"❌ Error scraping '{query}': {e}\n")

    print(f"✅ All scraping tasks completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}!\n")

def start_scraper_job():
    """
    Wrapper for running async scraper in APScheduler.
    """
    asyncio.run(scrape_all())

def schedule_scraping(frequency: str, time: str = "03:00", day_of_week: str = "sun"):
    """
    Schedule scraping job dynamically.
    :param frequency: 'hourly', 'daily', 'weekly'
    :param time: 'HH:MM' for daily/weekly
    :param day_of_week: 'mon', 'tue', ..., 'sun' for weekly
    """
    # Remove previous jobs
    scheduler.remove_all_jobs()

    # Parse hour and minute from time string
    try:
        hour, minute = map(int, time.split(":"))
    except ValueError:
        print("❌ Invalid time format. Use 'HH:MM'")
        return

    if frequency == "hourly":
        scheduler.add_job(
            start_scraper_job,
            trigger=IntervalTrigger(hours=1),
            id="scrape_job",
            replace_existing=True
        )
        print("✅ Scheduled hourly scraping job")

    elif frequency == "daily":
        scheduler.add_job(
            start_scraper_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="scrape_job",
            replace_existing=True
        )
        print(f"✅ Scheduled daily scraping job at {time}")

    elif frequency == "weekly":
        scheduler.add_job(
            start_scraper_job,
            trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
            id="scrape_job",
            replace_existing=True
        )
        print(f"✅ Scheduled weekly scraping job on {day_of_week} at {time}")

    else:
        print("❌ Invalid frequency. Choose 'hourly', 'daily', or 'weekly'.")

if __name__ == "__main__":
    # Example usage (uncomment one to schedule at startup)
    # schedule_scraping("hourly")
    # schedule_scraping("daily", time="03:00")
    # schedule_scraping("weekly", time="02:00", day_of_week="sun")

    print("🚀 Scraper scheduler started... Press Ctrl+C to exit.")
    scheduler.start()
