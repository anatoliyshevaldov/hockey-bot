from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramForbiddenError
from datetime import datetime
import aiosqlite, os

import database as db
from keyboards.player_kb import main_menu_kb, teams_list_kb, events_list_kb, event_detail_kb, my_events_kb

router = Router()
DB_PATH = os.getenv("DB_PATH", "hockey.db")

def fmt_date(s): return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m.%Y")
def type_icon(t): return "🏋️" if t == "training" else "🏒"

async def get_or_ask_name(message: Message) -> str | None:
    user = await db.get_user(message.from_user.id)
    if user and user["full_name"]:
        return user["full_name"]
    await message.answer(
        "👤 Сначала нужно зарегистрироваться.\nОтправь /start и введи Имя и Фамилию."
    )
    return None

# ── Schedule (trainings) ───────────────────────────────────────────────

@router.message(Command("schedule"))
@router.message(F.text == "🏋️ Тренировки")
async def cmd_schedule(message: Message):
    if not await get_or_ask_name(message): return
    teams = await db.get_teams()
    if not teams:
        await message.answer("😔 Команд пока нет."); return
    await message.answer("👥 Выбери команду:", reply_markup=teams_list_kb(teams, prefix="team_tr"))

@router.callback_query(F.data.startswith("team_tr_"))
async def show_team_trainings(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[2])
    events = await db.get_upcoming_events(team_id=team_id, type_="training")
    if not events:
        await callback.message.edit_text("😔 Нет тренировок.", reply_markup=teams_list_kb(await db.get_teams(), prefix="team_tr"))
        return
    await callback.message.edit_text("🏋️ <b>Тренировки:</b>", parse_mode="HTML",
                                     reply_markup=events_list_kb(events, f"team_tr_{team_id}"))

# ── Games ──────────────────────────────────────────────────────────────

@router.message(Command("games"))
@router.message(F.text == "🏒 Игры")
async def cmd_games(message: Message):
    if not await get_or_ask_name(message): return
    teams = await db.get_teams()
    if not teams:
        await message.answer("😔 Команд пока нет."); return
    await message.answer("👥 Выбери команду:", reply_markup=teams_list_kb(teams, prefix="team_gm"))

@router.callback_query(F.data.startswith("team_gm_"))
async def show_team_games(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[2])
    events = await db.get_upcoming_events(team_id=team_id, type_="game")
    if not events:
        await callback.message.edit_text("😔 Нет игр.", reply_markup=teams_list_kb(await db.get_teams(), prefix="team_gm"))
        return
    await callback.message.edit_text("🏒 <b>Игры:</b>", parse_mode="HTML",
                                     reply_markup=events_list_kb(events, f"team_gm_{team_id}"))

# ── Event detail ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("event_detail_"))
async def show_event_detail(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True); return

    user_reg = await db.get_user_registration(event_id, callback.from_user.id)
    spots_left = event["max_players"] - event["confirmed_count"]
    spots_text = f"{spots_left} свободно" if spots_left > 0 else "Мест нет"

    status_text = ""
    if user_reg:
        status_text = "\n\n✅ <b>Ты записан!</b>" if user_reg["status"] == "confirmed" else "\n\n⏳ <b>Ты в листе ожидания.</b>"

    text = (
        f"{type_icon(event['type'])} <b>{event['title']}</b>\n"
        f"👥 {event['team_name']} · 📅 {fmt_date(event['event_date'])} {event['event_time']}\n"
    )
    if event["location"]: text += f"📍 {event['location']}\n"
    if event["description"]: text += f"📝 {event['description']}\n"
    text += (
        f"\n👤 Записано: {event['confirmed_count']}/{event['max_players']} ({spots_text})\n"
        f"⏳ Лист ожидания: {event['waitlist_count']}{status_text}"
    )

    back = f"team_tr_{event['team_id']}" if event["type"] == "training" else f"team_gm_{event['team_id']}"
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=event_detail_kb(event_id, back, user_reg))

# ── Players list ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("players_list_"))
async def show_players_list(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    regs = await db.get_event_registrations(event_id)

    confirmed = regs["confirmed"]
    waitlist = regs["waitlist"]

    text = f"{type_icon(event['type'])} <b>{event['title']}</b> · {fmt_date(event['event_date'])} {event['event_time']}\n\n"

    if confirmed:
        text += f"✅ <b>Записаны ({len(confirmed)}/{event['max_players']}):</b>\n"
        for i, r in enumerate(confirmed, 1):
            text += f"  {i}. {r['full_name']}\n"
    else:
        text += "✅ Записей пока нет.\n"

    if waitlist:
        text += f"\n⏳ <b>Лист ожидания ({len(waitlist)}):</b>\n"
        for i, r in enumerate(waitlist, 1):
            text += f"  {i}. {r['full_name']}\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"event_detail_{event_id}")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())

# ── Register ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("register_"))
async def register_for_event(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    user = callback.from_user

    db_user = await db.get_user(user.id)
    if not db_user or not db_user["full_name"]:
        await callback.answer("Сначала пройди регистрацию — отправь /start", show_alert=True)
        return

    full_name = db_user["full_name"]
    result = await db.register_user(event_id, user.id, user.username, full_name)
    event = await db.get_event(event_id)

    if result == "already_registered":
        await callback.answer("Ты уже записан!", show_alert=True); return
    elif result == "confirmed":
        await callback.answer("✅ Ты записан!", show_alert=True)
        text = f"✅ <b>Запись подтверждена!</b>\n\n{type_icon(event['type'])} {event['title']}\n📅 {fmt_date(event['event_date'])} {event['event_time']}"
    else:
        await callback.answer("⏳ Добавлен в лист ожидания!", show_alert=True)
        text = f"⏳ <b>Ты в листе ожидания</b>\n\n{type_icon(event['type'])} {event['title']}\n📅 {fmt_date(event['event_date'])} {event['event_time']}"

    await callback.message.answer(text, parse_mode="HTML")

    # Notify admins
    admins = await db.get_admins()
    for admin in admins:
        try:
            await callback.bot.send_message(admin["user_id"],
                f"🔔 <b>Новая запись</b>\n{full_name} (@{user.username or '—'})\n"
                f"{type_icon(event['type'])} {event['title']} · {fmt_date(event['event_date'])}\n"
                f"{'✅ Подтверждён' if result == 'confirmed' else '⏳ Лист ожидания'}",
                parse_mode="HTML")
        except TelegramForbiddenError:
            pass

    # Refresh detail
    await show_event_detail(callback)

# ── Cancel registration ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_reg_"))
async def cancel_registration(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    promoted_uid = await db.cancel_registration(event_id, callback.from_user.id)
    event = await db.get_event(event_id)
    await callback.answer("❌ Запись отменена.", show_alert=True)

    if promoted_uid:
        try:
            await callback.bot.send_message(promoted_uid,
                f"🎉 <b>Место освободилось!</b>\n\nТы переведён в список участников:\n"
                f"{type_icon(event['type'])} {event['title']}\n📅 {fmt_date(event['event_date'])} {event['event_time']}",
                parse_mode="HTML")
        except TelegramForbiddenError:
            pass

    await show_event_detail(callback)

# ── My events ──────────────────────────────────────────────────────────

@router.message(Command("myevents"))
@router.message(F.text == "🎯 Мои записи")
async def my_events(message: Message):
    if not await get_or_ask_name(message): return

    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT e.*, t.name as team_name, r.status as reg_status
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            JOIN teams t ON e.team_id = t.id
            WHERE r.user_id = ? AND r.status != 'cancelled'
              AND e.status = 'active' AND e.event_date >= DATE('now')
            ORDER BY e.event_date, e.event_time
        """, (message.from_user.id,))
        events = await cursor.fetchall()

    if not events:
        await message.answer("У тебя нет активных записей.", reply_markup=main_menu_kb()); return

    text = "🎯 <b>Мои записи:</b>\n\n"
    for e in events:
        st = "✅" if e["reg_status"] == "confirmed" else "⏳"
        text += f"{st} {type_icon(e['type'])} <b>{e['title']}</b>\n   📅 {fmt_date(e['event_date'])} {e['event_time']} · {e['team_name']}\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=my_events_kb(events))

@router.callback_query(F.data.startswith("myevent_cancel_"))
async def cancel_from_my_events(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    promoted_uid = await db.cancel_registration(event_id, callback.from_user.id)
    event = await db.get_event(event_id)
    await callback.answer("❌ Запись отменена.", show_alert=True)

    if promoted_uid:
        try:
            await callback.bot.send_message(promoted_uid,
                f"🎉 <b>Место освободилось!</b>\n{type_icon(event['type'])} {event['title']}\n📅 {fmt_date(event['event_date'])} {event['event_time']}",
                parse_mode="HTML")
        except TelegramForbiddenError:
            pass

    # Refresh my events
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT e.*, t.name as team_name, r.status as reg_status
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            JOIN teams t ON e.team_id = t.id
            WHERE r.user_id = ? AND r.status != 'cancelled'
              AND e.status = 'active' AND e.event_date >= DATE('now')
            ORDER BY e.event_date, e.event_time
        """, (callback.from_user.id,))
        events = await cursor.fetchall()

    if not events:
        await callback.message.edit_text("У тебя нет активных записей.")
        return

    text = "🎯 <b>Мои записи:</b>\n\n"
    for e in events:
        st = "✅" if e["reg_status"] == "confirmed" else "⏳"
        text += f"{st} {type_icon(e['type'])} <b>{e['title']}</b>\n   📅 {fmt_date(e['event_date'])} {e['event_time']} · {e['team_name']}\n\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=my_events_kb(events))

# ── Help ───────────────────────────────────────────────────────────────

@router.message(F.text == "ℹ️ Помощь")
async def help_button(message: Message):
    await message.answer(
        "📋 <b>Как пользоваться:</b>\n\n"
        "🏋️ <b>Тренировки</b> — расписание тренировок, запись\n"
        "🏒 <b>Игры</b> — расписание матчей, запись\n"
        "🎯 <b>Мои записи</b> — твои записи, отмена одной кнопкой\n\n"
        "При записи автоматически попадёшь в лист ожидания если мест нет.\n"
        "Напоминание придёт за день до события.",
        parse_mode="HTML", reply_markup=main_menu_kb()
    )
