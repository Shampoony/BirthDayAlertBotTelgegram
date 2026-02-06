import asyncio
import logging
import sys

from aiogram import Dispatcher

from app.db.models import async_main
from scheduler import start_scheduler   # ✅ только эту функцию импортируем
from app.handlers import router
from config import bot


async def main():
    # подключение к БД
    await async_main()

    # стартуем планировщик
    start_scheduler()

    # настраиваем диспетчер
    dp = Dispatcher()
    dp.include_router(router)

    # запускаем бота
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
