# test_email.py
import asyncio
from utils.email_notifier import send_failure_email

async def main():
    await send_failure_email("Test error message – email system check", "manual-test")

if __name__ == "__main__":
    asyncio.run(main())
