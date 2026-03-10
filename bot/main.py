import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import label, sgr, start

load_dotenv()
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Store backend URL in bot data for handlers
    dp["backend_url"] = BACKEND_URL

    dp.include_router(start.router)
    dp.include_router(sgr.router)
    dp.include_router(label.router)

    logging.info("Bot starting... Backend: %s", BACKEND_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
