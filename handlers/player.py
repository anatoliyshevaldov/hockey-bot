from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from datetime import datetime

import database as db
from keyboards.player_kb import (
    main_menu_kb, teams_list_kb, events_list_kb,
    event_detail_kb, my_events_kb
)

router = Router()

def format_date(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")

def event_type_icon(type_: str) -> str:
    return "🏋️" if type_ == "training" else "🏒"

# ── Schedule ───────────────────────────────────────────────────────────

@router.message(Command("schedule"))
@router.message(F.text == "📅 Расписание")
async def cmd_schedule(message: Message):
    teams = await db.get_teams()
    if not teams:
        await message.answer("😔 Пока нет ни одной команды. Обратись к администратору.")
        return
    await message.answer("👥 Выбери команду:", reply_markup=teams_list_kb(teams))

@router.callback_query(F.data.startswith("team_events_"))
async def show_team_events(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[2])
    events = await db.get_upcoming_events(team_id)
    if not events:
        await callback.message.edit_text(
            "😔 Нет предстоящих событий для этой команды.",
            reply_markup=teams_list_kb(await db.get_teams())
        )
        return
    await callback.message.edit_text(
        "📅 <b>Предстоящие события:</b>",
        parse_mode="HTML",
        reply_markup=events_list_kb(events, team_id)
    )

@router.callback_query(F.data.startswith("event_detail_"))
async def show_event_detail(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    user_reg = await db.get_user_registration(event_id, callback.from_user.id)

    status_text = ""
    if user_reg:
        if user_reg["status"] == "confirmed":
            status_text = "\n\n✅ <b>Ты записан!</b>"
        elif user_reg["status"] == "waitlist":
            status_text = "\n\n⏳ <b>Ты в листе ожидания.</b>"

    spots_left = event["max_players"] - event["confirmed_count"]
    spots_text = f"{spots_left} свободно" if spots_left > 0 else "Мест нет (есть лист ожидания)"

    text = (
        f"{event_type_icon(event['type'])} <b>{event['title']}</b>\n"
        f"👥 Команда: {event['team_name']}\n"
        f"📅 {format_date(event['event_date'])} в {event['event_time']}\n"
    )
    if event["location"]:
        text += f"📍 {event['location']}\n"
    if event["description"]:
        text += f"📝 {event['description']}\n"
    text += (
        f"\n👤 Записано: {event['confirmed_count']}/{event['max_players']} ({spots_text})\n"
        f"⏳ Лист ожидания: {event['waitlist_count']}"
        f"{status_text}"
    )

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=event_detail_kb(event_id, event["team_id"], user_reg)
    )

# ── Register ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("register_"))
async def register_for_event(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    user = callback.from_user
    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    result = await db.register_user(event_id, user.id, user.username, full_name)
    event = await db.get_event(event_id)

    if result == "already_registered":
        await callback.answer("Ты уже записан на это событие!", show_alert=True)
        return
    elif result == "confirmed":
        await callback.answer("✅ Ты записан!", show_alert=True)
        msg_text = (
            f"✅ <b>Запись подтверждена!</b>\n\n"
            f"{event_type_icon(event['type'])} {event['title']}\n"
            f"📅 {format_date(event['event_date'])} в {event['event_time']}\n"
        )
        if event["location"]:
            msg_text += f"📍 {event['location']}"
    else:
        await callback.answer("⏳ Мест нет. Ты добавлен в лист ожидания!", show_alert=True)
        msg_text = (
            f"⏳ <b>Ты в листе ожидания</b>\n\n"
            f"{event_type_icon(event['type'])} {event['title']}\n"
            f"📅 {format_date(event['event_date'])} в {event['event_time']}\n"
            f"Мы уведомим тебя, если освободится место."
        )

    await callback.message.answer(msg_text, parse_mode="HTML")

    # Notify admins
    admins = await db.get_admins()
    for admin in admins:
        try:
            await callback.bot.send_message(
                admin["user_id"],
                f"🔔 <b>Новая запись</b>\n\n"
                f"{full_name} (@{user.username or '—'}) записался на:\n"
                f"{event_type_icon(event['type'])} {event['title']}\n"
                f"📅 {format_date(event['event_date'])} в {event['event_time']}\n"
                f"Статус: {'✅ Подтверждён' if result == 'confirmed' else '⏳ Лист ожидания'}",
                parse_mode="HTML"
            )
        except TelegramForbiddenError:
            pass

    # Refresh message
    user_reg = await db.get_user_registration(event_id, user.id)
    event = await db.get_event(event_id)
    spots_left = event["max_players"] - event["confirmed_count"]
    spots_text = f"{spots_left} свободно" if spots_left > 0 else "Мест нет (есть лист ожидания)"

    status_text = "✅ <b>Ты записан!</b>" if result == "confirmed" else "⏳ <b>Ты в листе ожидания.</b>"
    text = (
        f"{event_type_icon(event['type'])} <b>{event['title']}</b>\n"
        f"📅 {format_date(event['event_date'])} в {event['event_time']}\n"
        f"👤 Записано: {event['confirmed_count']}/{event['max_players']} ({spots_text})\n"
        f"⏳ Лист ожидания: {event['waitlist_count']}\n\n"
        f"{status_text}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=event_detail_kb(event_id, event["team_id"], user_reg))

# ── Cancel registration ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_reg_"))
async def cancel_registration(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    promoted_uid = await db.cancel_registration(event_id, callback.from_user.id)
    event = await db.get_event(event_id)

    await callback.answer("❌ Запись отменена.", show_alert=True)

    if promoted_uid:
        try:
            await callback.bot.send_message(
                promoted_uid,
                f"🎉 <b>Место освободилось!</b>\n\n"
                f"Ты переведён из листа ожидания в список участников:\n"
                f"{event_type_icon(event['type'])} {event['title']}\n"
                f"📅 {format_date(event['event_date'])} в {event['event_time']}",
                parse_mode="HTML"
            )
        except TelegramForbiddenError:
            pass

    await callback.message.edit_text(
        f"❌ Запись на <b>{event['title']}</b> отменена.",
        parse_mode="HTML",
        reply_markup=teams_list_kb(await db.get_teams())
    )

# ── My events ──────────────────────────────────────────────────────────

@router.message(Command("myevents"))
@router.message(F.text == "🎯 Мои записи")
async def my_events(message: Message):
    async with __import__("aiosqlite").connect(__import__("os").getenv("DB_PATH", "hockey.db")) as db_conn:
        db_conn.row_factory = __import__("aiosqlite").Row
        cursor = await db_conn.execute("""
            SELECT e.*, t.name as team_name, r.status as reg_status
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            JOIN teams t ON e.team_id = t.id
            WHERE r.user_id = ? AND r.status != 'cancelled' AND e.status = 'active' AND e.event_date >= DATE('now')
            ORDER BY e.event_date, e.event_time
        """, (message.from_user.id,))
        events = await cursor.fetchall()

    if not events:
        await message.answer("У тебя нет активных записей.", reply_markup=main_menu_kb())
        return

    text = "🎯 <b>Твои записи:</b>\n\n"
    for e in events:
        icon = event_type_icon(e["type"])
        status = "✅" if e["reg_status"] == "confirmed" else "⏳"
        text += f"{status} {icon} <b>{e['title']}</b>\n   📅 {format_date(e['event_date'])} {e['event_time']} · {e['team_name']}\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=my_events_kb(events))

@router.callback_query(F.data.startswith("myevent_"))
async def my_event_detail(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    user_reg = await db.get_user_registration(event_id, callback.from_user.id)
    await show_event_detail.__wrapped__(callback) if hasattr(show_event_detail, "__wrapped__") else None
    # Re-use show_event_detail logic
    callback.data = f"event_detail_{event_id}"
    await show_event_detail(callback)

# ── Main menu button ───────────────────────────────────────────────────

@router.message(F.text == "ℹ️ Помощь")
async def help_button(message: Message):
    await message.answer(
        "📋 <b>Как пользоваться ботом:</b>\n\n"
        "1. Нажми <b>📅 Расписание</b> — выбери команду и событие\n"
        "2. Нажми <b>Записаться</b> — ты попадёшь в список участников\n"
        "3. Если мест нет — попадёшь в <b>лист ожидания</b>\n"
        "4. Отменить запись можно в любое время в <b>🎯 Мои записи</b>\n"
        "5. За день до события придёт <b>напоминание</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
