from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Установить дату', callback_data='set_date')],
    [InlineKeyboardButton(text='Просмотреть все свои даты', callback_data='check_date')]
])

setmotre = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Добавить ещё', callback_data='set_date')]
])

setkeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='◀️ Назад', callback_data='cancel_setdate'),
        InlineKeyboardButton(text='❌ Отменить', callback_data='back_setdate'),
    ]
])


def suredelete (date_id):
    return InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='✅ Удалить', callback_data=f'delete_{date_id}'),
        InlineKeyboardButton(text='◀️ Назад', callback_data=f'date_{date_id}')
    ]
])
    

def dates_function_kbs(date_id):
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🗑️ Удалить', callback_data=f'sure_delete_{date_id}'), InlineKeyboardButton(text='✏️ Редактировать', callback_data=f'edit_{date_id}')],
    [InlineKeyboardButton(text='⬅️ Назад', callback_data='check_date')]
])

def timezone_keyboard():
    buttons = [
        InlineKeyboardButton(text=f"UTC{i:+}", callback_data=f"tz_{i}")
        for i in range(-12, 15)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i+4] for i in range(0, len(buttons), 4)]
    )

def my_dates_keyboard(items, page: int, total_pages: int):
    """
    items: список UserItem для текущей страницы
    page: текущая страница (0-index)
    total_pages: общее количество страниц
    """
    if not items:
        return None

    keyboard = InlineKeyboardBuilder()

    # Кнопки с датами
    for date in items:
        keyboard.add(
            InlineKeyboardButton(
                text=f"{date.name} ({date.date})",
                callback_data=f"date_{date.id}"
            )
        )

    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"dates_page_{page-1}")
        )
    if page + 1 < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"dates_page_{page+1}")
        )
    if nav_buttons:
        keyboard.row(*nav_buttons)

    # Главное меню
    keyboard.add(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main")
    )

    return keyboard.adjust(2).as_markup()