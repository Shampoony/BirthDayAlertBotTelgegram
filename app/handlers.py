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
from app.db.requests import set_useritem, get_user_items_block, get_user_item_by_id, delete_date_by_id, update_user_item

router = Router()

# ---- Состояния ----
class SetDate(StatesGroup):
    name = State()
    username = State()
    timezone = State()
    date = State()
    time = State()


# ---- Клавиатура часовых поясов ----
def timezone_keyboard(with_leave_button: bool = False):
    buttons = [
        InlineKeyboardButton(text=f"UTC{i:+}", callback_data=f"tz_{i}")
        for i in range(-12, 15)
    ]
    
    # Разбиваем по 4 кнопки в ряд
    keyboard = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    
    if with_leave_button:
        leave_button = [InlineKeyboardButton(text="Оставить текущий", callback_data="tz_leave")]
        keyboard.append(leave_button)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ---- Старт ----
@router.message(CommandStart() )
async def cmd_start(message: Message):
    await message.answer(
        "🎉 Добро пожаловать!\n\nНажмите кнопку ниже, чтобы добавить дату 🎂",
        reply_markup=kb.main
    )

@router.callback_query(F.data == 'main')
async def cmd_start(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
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

    await callback.message.answer(
        "🎉 Добро пожаловать!\n\nНажмите кнопку ниже, чтобы добавить дату 🎂",
        reply_markup=kb.main
    )


@router.callback_query(F.data.startswith('edit_'))
async def edit_date(callback: CallbackQuery, state: FSMContext):
    date_id = callback.data.split('_')[1]
    existing = await get_user_item_by_id(int(date_id))

    if not existing:
        await callback.answer("Запись не найдена 😔", show_alert=True)
        return

    await state.update_data(
        edit_mode=True,
        date_id=date_id,
        name=getattr(existing, "name", ""),
        username=getattr(existing, "username", ""),
        timezone_offset=getattr(existing, "timezone_offset", 0),
        date=getattr(existing, "date", ""),
        time=getattr(existing, "time", ""),
        datetime_utc=getattr(existing, "datetime_utc", None),
    )

    await callback.message.answer(
        "✏️ Редактирование\n\n"
        f"Текущее имя: {existing.name or '—'}\n"
        "Введите новое имя или «-»"
    )

    await state.set_state(SetDate.name)
    await callback.answer()


# ===================== NAME =====================

@router.message(SetDate.name)
async def set_name(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        if text != "-":
            if len(text) < 2:
                await message.answer("❗ Имя слишком короткое")
                return
            await state.update_data(name=text)
    else:
        if len(text) < 2:
            await message.answer("❗ Имя слишком короткое")
            return
        await state.update_data(name=text)

    await state.set_state(SetDate.username)

    if edit_mode:
        await message.answer(
            f"Текущий username: {data.get('username', '—')}\n\n"
            "Введите новый или «-»"
        )
    else:
        await message.answer("Введите username:")


# ===================== USERNAME =====================

@router.message(SetDate.username)
async def set_username(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        if text != "-":
            if not is_valid_username(text):
                await message.answer("❗ Некорректный username")
                return
            await state.update_data(username=text)
    else:
        if not is_valid_username(text):
            await message.answer("❗ Некорректный username")
            return
        await state.update_data(username=text)

    await state.set_state(SetDate.timezone)

    if edit_mode:
        tz = data.get("timezone_offset", 0) // 3600
        await message.answer(
            f"Текущий часовой пояс (UTC{tz:+d})\n\n"
            "Выберите новый или «Оставить»",
            reply_markup=timezone_keyboard(with_leave_button=True)
        )
    else:
        await message.answer(
            "Выберите часовой пояс:",
            reply_markup=timezone_keyboard()
        )


# ===================== TIMEZONE =====================

@router.callback_query(F.data.startswith("tz_"), SetDate.timezone)
async def set_timezone(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if callback.data == "tz_leave":
        pass
    else:
        offset = int(callback.data.replace("tz_", ""))
        await state.update_data(timezone_offset=offset * 3600)

    await state.set_state(SetDate.date)

    if edit_mode:
        await callback.message.answer(
            f"Текущая дата: {data.get('date', '—')}\n\n"
            "Введите новую или «-»"
        )
    else:
        await callback.message.answer("Введите дату (ДД.ММ.ГГГГ):")

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

    await callback.answer()


# ===================== DATE =====================

@router.message(SetDate.date)
async def handle_date_text(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        if text != "-":
            if not is_valid_date(text):
                await message.answer("❗ Формат: ДД.ММ.ГГГГ")
                return
            await state.update_data(date=text)
    else:
        if not is_valid_date(text):
            await message.answer("❗ Формат: ДД.ММ.ГГГГ")
            return
        await state.update_data(date=text)

    await state.set_state(SetDate.time)

    if edit_mode:
        await message.answer(
            f"Текущее время: {data.get('time', '—')}\n\n"
            "Введите новое или «-»"
        )
    else:
        await message.answer("Введите время (HH:MM):")


# ===================== CALENDAR =====================

@router.callback_query(SimpleCalendarCallback.filter(), SetDate.date)
async def handle_calendar(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)

    if selected:
        await state.update_data(date=date.strftime("%d.%m.%Y"))
        await state.set_state(SetDate.time)
        await callback.message.answer("Введите время (HH:MM):")


# ===================== TIME =====================

@router.message(SetDate.time)
async def handle_time(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        if text == "-":
            time_str = data.get("time", "00:00")
        else:
            try:
                datetime.strptime(text, "%H:%M")
                time_str = text
                await state.update_data(time=time_str)
            except ValueError:
                await message.answer("❗ Формат: HH:MM")
                return
    else:
        try:
            datetime.strptime(text, "%H:%M")
            time_str = text
            await state.update_data(time=time_str)
        except ValueError:
            await message.answer("❗ Формат: HH:MM")
            return

    tz_offset = data.get("timezone_offset", 0)
    user_tz = timezone(timedelta(seconds=tz_offset))

    date_str = data.get("date")

    local_dt = datetime.strptime(
        f"{date_str} {time_str}",
        "%d.%m.%Y %H:%M"
    ).replace(tzinfo=user_tz)

    utc_dt = local_dt.astimezone(timezone.utc)
    await state.update_data(datetime_utc=utc_dt.isoformat())

    itemdata = await state.get_data()

    if itemdata.get("edit_mode"):
        date_id = itemdata["date_id"]
        itemdata.pop("date_id")
        await update_user_item(date_id=date_id, itemdata=itemdata)
        text = "✅ Обновлено!"
    else:
        await set_useritem(
            userdata={
                "tg_id": message.from_user.id,
                "username": message.from_user.username
            },
            itemdata=itemdata
        )
        text = "✅ Сохранено!"

    schedule_birthday(
        chat_id=message.from_user.id,
        username=itemdata["username"],
        name=itemdata["name"],
        datetime_utc=itemdata["datetime_utc"],
        bot=message.bot
    )

    await message.answer(f"{text}\n📅 {date_str} {time_str}")
    await state.clear()

