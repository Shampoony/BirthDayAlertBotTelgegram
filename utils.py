import re
from datetime import datetime

def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False


def is_valid_username(value: str) -> bool:
    """
    Проверяет:
    - Telegram username: начинается с @ и содержит от 5 до 32 символов
    - Ссылку: https://t.me/username или любую https-ссылку
    """
    username_pattern = r"^@[\w\d_]{5,32}$"
    telegram_link = r"^https:\/\/t\.me\/[\w\d_]{5,32}$"
    any_url = r"^https?:\/\/[\S]+$"

    return bool(re.match(username_pattern, value) or
                re.match(telegram_link, value) or
                re.match(any_url, value))
