import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import API_TOKEN
from utils.database import init_db
from handlers import client, admin


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(client.router)
    dp.include_router(admin.router)

    init_db()

    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот CafeHantHaus запущен!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
