import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError

import database as db
from keyboards.admin_kb import (
    admin_menu_kb, teams_list_kb, event_type_kb,
    teams_for_event_kb, cancel_kb, events_admin_list_kb
)

router = Router()

SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))

# ── States ─────────────────────────────────────────────────────────────

class CreateTeam(StatesGroup):
    name = State()

class CreateEvent(StatesGroup):
    type = State()
    team = State()
    title = State()
    date = State()
    time = State()
    location = State()
    max_players = State()
    description = State()

class AddAdmin(StatesGroup):
    user_id = State()

# ── Admin check ────────────────────────────────────────────────────────

async def admin_required(message_or_cb):
    obj = message_or_cb
    user_id = obj.from_user.id
    if not await db.is_admin(user_id) and user_id != SUPER_ADMIN_ID:
        text = "⛔ У тебя нет прав администратора."
        if hasattr(obj, "answer"):
            await obj.answer(text)
        else:
            await obj.message.answer(text)
        return False
    return True

# ── Admin panel ────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if not await admin_required(message):
        return
    await message.answer("👑 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_menu_kb())

@router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await admin_required(callback):
        return
    await callback.message.edit_text("👑 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_menu_kb())

# ── Teams management ───────────────────────────────────────────────────

@router.callback_query(F.data == "manage_teams")
async def manage_teams(callback: CallbackQuery):
    if not await admin_required(callback):
        return
    teams = await db.get_teams()
    text = "🏒 <b>Управление командами</b>\n\nСписок команд:" if teams else "🏒 <b>Управление командами</b>\n\nКоманд пока нет."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=teams_list_kb(teams))

@router.callback_query(F.data == "add_team")
async def add_team_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await state.set_state(CreateTeam.name)
    await callback.message.edit_text("✏️ Введи название команды:", reply_markup=cancel_kb("manage_teams"))

@router.message(CreateTeam.name)
async def add_team_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Название слишком короткое. Попробуй ещё раз:")
        return
    try:
        await db.create_team(name)
        await state.clear()
        teams = await db.get_teams()
        await message.answer(f"✅ Команда <b>{name}</b> создана!", parse_mode="HTML", reply_markup=teams_list_kb(teams))
    except Exception:
        await message.answer("❌ Команда с таким названием уже существует.")

@router.callback_query(F.data.startswith("delete_team_"))
async def delete_team(callback: CallbackQuery):
    if not await admin_required(callback):
        return
    team_id = int(callback.data.split("_")[2])
    await db.delete_team(team_id)
    teams = await db.get_teams()
    await callback.message.edit_text("🗑 Команда удалена.\n\nСписок команд:", parse_mode="HTML", reply_markup=teams_list_kb(teams))

# ── Create event ───────────────────────────────────────────────────────

@router.callback_query(F.data == "create_event")
async def create_event_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await state.set_state(CreateEvent.type)
    await callback.message.edit_text("🏒 Выбери тип события:", reply_markup=event_type_kb())

@router.callback_query(F.data.startswith("etype_"), CreateEvent.type)
async def create_event_type(callback: CallbackQuery, state: FSMContext):
    event_type = callback.data.split("_")[1]
    await state.update_data(type=event_type)
    teams = await db.get_teams()
    if not teams:
        await callback.message.edit_text("❌ Сначала создай команду в разделе 'Команды'.", reply_markup=admin_menu_kb())
        await state.clear()
        return
    await state.set_state(CreateEvent.team)
    await callback.message.edit_text("👥 Выбери команду:", reply_markup=teams_for_event_kb(teams))

@router.callback_query(F.data.startswith("eteam_"), CreateEvent.team)
async def create_event_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[1])
    await state.update_data(team_id=team_id)
    await state.set_state(CreateEvent.title)
    await callback.message.edit_text("✏️ Введи название события (например: «Тренировка №5» или «Игра с Динамо»):", reply_markup=cancel_kb("admin_menu"))

@router.message(CreateEvent.title)
async def create_event_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateEvent.date)
    await message.answer("📅 Введи дату в формате <b>ДД.ММ.ГГГГ</b> (например: 25.01.2025):", parse_mode="HTML")

@router.message(CreateEvent.date)
async def create_event_date(message: Message, state: FSMContext):
    from datetime import datetime
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        await state.update_data(event_date=date.strftime("%Y-%m-%d"))
        await state.set_state(CreateEvent.time)
        await message.answer("🕐 Введи время в формате <b>ЧЧ:ММ</b> (например: 19:30):", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Неверный формат. Введи дату как <b>ДД.ММ.ГГГГ</b>:", parse_mode="HTML")

@router.message(CreateEvent.time)
async def create_event_time(message: Message, state: FSMContext):
    import re
    if not re.match(r"^\d{2}:\d{2}$", message.text.strip()):
        await message.answer("❌ Неверный формат. Введи время как <b>ЧЧ:ММ</b>:", parse_mode="HTML")
        return
    await state.update_data(event_time=message.text.strip())
    await state.set_state(CreateEvent.location)
    await message.answer("📍 Введи место проведения (или отправь <b>-</b> чтобы пропустить):", parse_mode="HTML")

@router.message(CreateEvent.location)
async def create_event_location(message: Message, state: FSMContext):
    location = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(location=location)
    await state.set_state(CreateEvent.max_players)
    await message.answer("👥 Введи максимальное количество игроков (например: <b>20</b>):", parse_mode="HTML")

@router.message(CreateEvent.max_players)
async def create_event_max(message: Message, state: FSMContext):
    try:
        max_p = int(message.text.strip())
        if max_p < 1 or max_p > 100:
            raise ValueError
        await state.update_data(max_players=max_p)
        await state.set_state(CreateEvent.description)
        await message.answer("📝 Введи описание (или отправь <b>-</b> чтобы пропустить):", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введи число от 1 до 100:")

@router.message(CreateEvent.description)
async def create_event_description(message: Message, state: FSMContext):
    description = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    event_id = await db.create_event(
        team_id=data["team_id"],
        type_=data["type"],
        title=data["title"],
        description=description,
        event_date=data["event_date"],
        event_time=data["event_time"],
        location=data.get("location"),
        max_players=data["max_players"]
    )

    type_label = "🏋️ Тренировка" if data["type"] == "training" else "🏒 Игра/матч"
    from datetime import datetime
    date_str = datetime.strptime(data["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")

    await message.answer(
        f"✅ <b>Событие создано!</b>\n\n"
        f"{type_label}: <b>{data['title']}</b>\n"
        f"📅 {date_str} в {data['event_time']}\n"
        f"👥 Мест: {data['max_players']}\n"
        f"🆔 ID: {event_id}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )

# ── View & cancel events ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_events")
async def admin_events(callback: CallbackQuery):
    if not await admin_required(callback):
        return
    events = await db.get_upcoming_events()
    if not events:
        await callback.message.edit_text("📅 Нет предстоящих событий.", reply_markup=admin_menu_kb())
        return
    await callback.message.edit_text("📅 <b>Предстоящие события:</b>", parse_mode="HTML", reply_markup=events_admin_list_kb(events))

@router.callback_query(F.data.startswith("admin_event_"))
async def admin_event_detail(callback: CallbackQuery):
    if not await admin_required(callback):
        return
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    regs = await db.get_event_registrations(event_id)

    from datetime import datetime
    date_str = datetime.strptime(event["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    type_label = "🏋️ Тренировка" if event["type"] == "training" else "🏒 Игра/матч"

    confirmed_list = "\n".join(
        [f"  {i+1}. {r['full_name']} (@{r['username']})" if r['username'] else f"  {i+1}. {r['full_name']}"
         for i, r in enumerate(regs["confirmed"])]
    ) or "  —"

    waitlist_list = "\n".join(
        [f"  {i+1}. {r['full_name']} (@{r['username']})" if r['username'] else f"  {i+1}. {r['full_name']}"
         for i, r in enumerate(regs["waitlist"])]
    ) or "  —"

    text = (
        f"{type_label} <b>{event['title']}</b>\n"
        f"👥 Команда: {event['team_name']}\n"
        f"📅 {date_str} в {event['event_time']}\n"
        f"📍 {event['location'] or 'Не указано'}\n\n"
        f"✅ Записаны ({event['confirmed_count']}/{event['max_players']}):\n{confirmed_list}\n\n"
        f"⏳ Лист ожидания ({event['waitlist_count']}):\n{waitlist_list}"
    )

    from keyboards.admin_kb import event_detail_kb
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=event_detail_kb(event_id))

@router.callback_query(F.data.startswith("cancel_event_"))
async def cancel_event_confirm(callback: CallbackQuery):
    if not await admin_required(callback):
        return
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)

    user_ids = await db.get_all_registered_user_ids(event_id)
    await db.cancel_event(event_id)

    from datetime import datetime
    date_str = datetime.strptime(event["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")

    notified = 0
    for uid in user_ids:
        try:
            await callback.bot.send_message(
                uid,
                f"❌ <b>Событие отменено!</b>\n\n"
                f"🏒 {event['title']}\n"
                f"📅 {date_str} в {event['event_time']}\n"
                f"👥 {event['team_name']}",
                parse_mode="HTML"
            )
            notified += 1
        except TelegramForbiddenError:
            pass

    await callback.message.edit_text(
        f"✅ Событие отменено. Уведомлено игроков: {notified}",
        reply_markup=admin_menu_kb()
    )

# ── Add admin ──────────────────────────────────────────────────────────

@router.message(Command("addadmin"))
async def add_admin_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID and not await db.is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /addadmin <user_id>")
        return
    try:
        uid = int(args[1])
        await db.add_admin(uid, None, f"Admin {uid}")
        await message.answer(f"✅ Пользователь {uid} добавлен как администратор.")
    except ValueError:
        await message.answer("❌ Неверный user_id.")
