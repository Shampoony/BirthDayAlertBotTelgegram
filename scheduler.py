import logging
from urllib.parse import quote_plus
from datetime import datetime, timezone
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram.utils.text_decorations import html_decoration as hd

from api.api import get_birthday_congratulation

# ---------- ЛОГИ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scheduler")

# ---------- ПЛАНИРОВЩИК (ТОЛЬКО UTC) ----------
scheduler = AsyncIOScheduler(timezone=timezone.utc)


# ---------- ДОБАВЛЕНИЕ ЗАДАЧИ ----------
def schedule_birthday(
    chat_id: int,
    username: str,
    name: str,
    datetime_utc: str,
    bot
):
    """
    Планирует напоминание по UTC datetime (ISO format)
    """
    logger.info("Добавляем задачу напоминания")

    remind_time = datetime.fromisoformat(datetime_utc)

    if remind_time.tzinfo is None:
        remind_time = remind_time.replace(tzinfo=timezone.utc)

    trigger = DateTrigger(run_date=remind_time)

    job_id = f"birthday_{chat_id}_{int(remind_time.timestamp())}"

    scheduler.add_job(
        send_birthday_message,
        trigger=trigger,
        args=[chat_id, username, name, bot],
        id=job_id,
        replace_existing=True
    )

    logger.info(f"Задача {job_id} добавлена на {remind_time.isoformat()}")


# ---------- ОТПРАВКА СООБЩЕНИЯ ----------
async def send_birthday_message(chat_id: int, username: str, name: str, bot):
    logger.info(f"Отправляем напоминание в чат {chat_id}")

    try:
        username = username.replace('@', '')

        congratulation = get_birthday_congratulation()
        mention = f"{username}" if username and username != "—" else name
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎉 <b>Сегодня день рождения!</b> 🎉\n\n"
                f"👉 @{mention} \n\n"
                f"{name} будет рад услышать ваши поздравления с его праздником!\n"
                f"🎂 Не забудь поздравить!\n\n"
                f"🎂 Поздравить можно этим текстом:\n\n"
                f"💬 <blockquote>{hd.quote(congratulation)}</blockquote>\n\n"
            ),
            parse_mode="HTML"
        )

        logger.info("Сообщение успешно отправлено")

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


# ---------- ЗАПУСК ----------
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Планировщик запущен (UTC)")
    else:
        logger.warning("Планировщик уже запущен")


# ---------- ОСТАНОВКА ----------
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")
    else:
        logger.warning("Планировщик уже остановлен")
