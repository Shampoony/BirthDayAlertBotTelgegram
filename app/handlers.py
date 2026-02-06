from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from datetime import datetime, timezone, timedelta

import app.keyboards as kb
from scheduler import schedule_birthday
from utils import is_valid_date, is_valid_username
from app.db.requests import set_useritem, get_user_items_block, get_user_item_by_id, delete_date_by_id

router = Router()

# ---- Состояния ----
class SetDate(StatesGroup):
    name = State()
    username = State()
    timezone = State()
    date = State()
    time = State()


# ---- Клавиатура часовых поясов ----
def timezone_keyboard():
    buttons = [
        InlineKeyboardButton(text=f"UTC{i:+}", callback_data=f"tz_{i}")
        for i in range(-12, 15)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i+4] for i in range(0, len(buttons), 4)]
    )


# ---- Старт ----
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎉 Добро пожаловать!\n\nНажмите кнопку ниже, чтобы добавить дату 🎂",
        reply_markup=kb.main
    )


# ---- Начало процесса ----
@router.callback_query(F.data == "set_date")
async def set_date(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    msg = await callback.message.answer("Введите *имя* 👤", parse_mode="Markdown")
    await state.set_state(SetDate.name)
    await state.update_data(bot_message_id=msg.message_id)
    await callback.answer()

# ---- Просмтратриваем все даты ----
@router.callback_query(F.data == 'check_date')
async def check_date(callback: CallbackQuery):
    tg_id = callback.from_user.id
    page = 0
    items, total_pages = await get_user_items_block(tg_id, page)
    await callback.message.delete()
    if not items:
        await callback.message.answer("❌ У вас пока нет записанных дат.")
        return

    keyboard = kb.my_dates_keyboard(items, page, total_pages)
    await callback.message.answer("😊 *Все ваши записанные даты:*", reply_markup=keyboard, parse_mode='Markdown')

# ---- Пагинация страниц ----
@router.callback_query(F.data.startswith("dates_page_"))
async def change_dates_page(callback: CallbackQuery):
    tg_id = callback.from_user.id
    page = int(callback.data.split("_")[-1])  # извлекаем номер страницы

    items, total_pages = await get_user_items_block(tg_id, page)

    if not items:
        await callback.message.answer("❌ Даты на этой странице не найдены.")
        return

    keyboard = kb.my_dates_keyboard(items, page, total_pages)
    await callback.message.edit_reply_markup(reply_markup=keyboard)


# ---- Находим дату ----
@router.callback_query(F.data.startswith('date_'))
async def get_date(callback: CallbackQuery):
    
    date_id = int(callback.data.split('_')[1])
    date = await get_user_item_by_id(date_id)
    keyboard = kb.dates_function_kbs(date_id)
    await callback.message.delete()

    await callback.message.answer(
        f'У <a href="t.me/{date.username.replace('@', '')}"><b>{date.name}</b></a> день рождения 🎂<b>{date.date}</b>\n\n'
        f'Если хотите удалить или редактировать — нажмите кнопки ниже',
        reply_markup=keyboard,
        parse_mode='HTML'
    )

# ---- Проверка, хотите ли вы удалить дату ----
@router.callback_query(F.data.startswith('sure_delete_'))
async def sure_delete(callback: CallbackQuery):
    date_id = callback.data.split('_')[2]
    await callback.message.delete()
    await callback.message.answer('*Вы уверены, что хотите удалить дату ❓*', parse_mode='MarkdownV2', reply_markup=kb.suredelete(date_id))

# ---- Удалить дату ----
@router.callback_query(F.data.startswith('delete_'))
async def delete_date(callback: CallbackQuery):

    date_id = callback.data.split('_')[1]
    await delete_date_by_id(date_id)
    await callback.answer("🗑 Дата удалена", show_alert=True)

    await callback.message.delete()

    


# ---- Имя ----
@router.message(SetDate.name)
async def set_name(message: Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("❗ Введите корректное имя")
        return

    await state.update_data(name=message.text.strip())
    await state.set_state(SetDate.username)
    await message.answer("Введите *username* или ссылку 🔗", parse_mode="Markdown")


# ---- Username ----
@router.message(SetDate.username)
async def set_username(message: Message, state: FSMContext):
    if not is_valid_username(message.text):
        await message.answer("❗ Некорректный username")
        return

    await state.update_data(username=message.text.strip())
    await state.set_state(SetDate.timezone)
    await message.answer(
        "🌍 Выберите *ваш часовой пояс*:",
        parse_mode="Markdown",
        reply_markup=timezone_keyboard()
    )


# ---- Часовой пояс ----
@router.callback_query(F.data.startswith("tz_"), SetDate.timezone)
async def set_timezone(callback: CallbackQuery, state: FSMContext):
    offset_hours = int(callback.data.replace("tz_", ""))
    await state.update_data(timezone_offset=offset_hours * 3600)

    await callback.message.edit_text(
        f"🌍 Часовой пояс установлен: UTC{offset_hours:+}\n\n"
        f"📅 Введите дату (ДД.ММ.ГГГГ) или выберите в календаре:"
    )

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

    await state.set_state(SetDate.date)
    await callback.answer()


# ---- Ввод даты текстом ----
@router.message(SetDate.date)
async def handle_date_text(message: Message, state: FSMContext):
    if not is_valid_date(message.text):
        await message.answer("❗ Формат даты: ДД.ММ.ГГГГ")
        return

    await state.update_data(date=message.text)
    await state.set_state(SetDate.time)
    await message.answer("⏰ Введите время (HH:MM)")


# ---- Календарь ----
@router.callback_query(SimpleCalendarCallback.filter(), SetDate.date)
async def handle_calendar(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(date=date.strftime("%d.%m.%Y"))
        await state.set_state(SetDate.time)
        await callback.message.answer("⏰ Введите время (HH:MM)")


# ---- Время ----
@router.message(SetDate.time)
async def handle_time(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
    except ValueError:
        await message.answer("❗ Формат времени: HH:MM")
        return

    data = await state.get_data()
    tz_offset = data["timezone_offset"]

    user_tz = timezone(timedelta(seconds=tz_offset))

    local_dt = datetime.strptime(
        f"{data['date']} {message.text}",
        "%d.%m.%Y %H:%M"
    ).replace(tzinfo=user_tz)

    utc_dt = local_dt.astimezone(timezone.utc)

    await state.update_data(
        time=message.text,
        datetime_utc=utc_dt.isoformat()
    )

    itemdata = await state.get_data()

    await set_useritem(
        userdata={
            "tg_id": message.from_user.id,
            "username": message.from_user.username
        },
        itemdata=itemdata
    )

    schedule_birthday(
        chat_id=message.from_user.id,
        username=itemdata["username"],
        name=itemdata["name"],
        datetime_utc=itemdata["datetime_utc"],
        bot=message.bot
    )

    await message.answer(
        f"✅ Сохранено!\n\n"
        f"📅 {data['date']} {message.text}\n"
        f"🌍 UTC{tz_offset // 3600:+}"
    )

    await state.clear()
