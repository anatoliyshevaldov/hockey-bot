import os
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError

import database as db
from keyboards.admin_kb import (
    admin_menu_kb, teams_list_kb, event_type_kb, teams_for_event_kb,
    cancel_kb, events_admin_list_kb, event_detail_admin_kb,
    permanent_players_kb, month_select_kb, teams_for_monthly_kb,
    registrations_list_kb
)

router = Router()
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))

def fmt_date(date_str): return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
def type_icon(t): return "🏋️" if t == "training" else "🏒"

async def admin_required(obj):
    uid = obj.from_user.id
    if not await db.is_admin(uid) and uid != SUPER_ADMIN_ID:
        text = "⛔ У тебя нет прав администратора."
        if hasattr(obj, "answer"):
            await obj.answer(text)
        else:
            await obj.message.answer(text)
        return False
    return True

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

class AddPermanentPlayer(StatesGroup):
    team = State()
    name = State()

# ── Admin panel ────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if not await admin_required(message): return
    await message.answer("👑 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_menu_kb())

@router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await admin_required(callback): return
    await callback.message.edit_text("👑 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_menu_kb())

# ── Teams ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "manage_teams")
async def manage_teams(callback: CallbackQuery):
    if not await admin_required(callback): return
    teams = await db.get_teams()
    text = "🏒 <b>Команды</b>" + ("\n\nНажми на команду чтобы удалить:" if teams else "\n\nКоманд пока нет.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=teams_list_kb(teams))

@router.callback_query(F.data == "add_team")
async def add_team_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_required(callback): return
    await state.set_state(CreateTeam.name)
    await callback.message.edit_text("✏️ Введи название команды:", reply_markup=cancel_kb("manage_teams"))

@router.message(CreateTeam.name)
async def add_team_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое. Попробуй ещё:"); return
    try:
        await db.create_team(name)
        await state.clear()
        await message.answer(f"✅ Команда <b>{name}</b> создана!", parse_mode="HTML",
                             reply_markup=teams_list_kb(await db.get_teams()))
    except Exception:
        await message.answer("❌ Команда с таким названием уже существует.")

@router.callback_query(F.data.startswith("delete_team_"))
async def delete_team(callback: CallbackQuery):
    if not await admin_required(callback): return
    await db.delete_team(int(callback.data.split("_")[2]))
    await callback.message.edit_text("🗑 Команда удалена.", parse_mode="HTML",
                                     reply_markup=teams_list_kb(await db.get_teams()))

# ── Create single event ────────────────────────────────────────────────

@router.callback_query(F.data == "create_event")
async def create_event_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_required(callback): return
    await state.set_state(CreateEvent.type)
    await callback.message.edit_text("🏒 Тип события:", reply_markup=event_type_kb())

@router.callback_query(F.data.startswith("etype_"), CreateEvent.type)
async def create_event_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(type=callback.data.split("_")[1])
    teams = await db.get_teams()
    if not teams:
        await callback.message.edit_text("❌ Сначала создай команду.", reply_markup=admin_menu_kb())
        await state.clear(); return
    await state.set_state(CreateEvent.team)
    await callback.message.edit_text("👥 Выбери команду:", reply_markup=teams_for_event_kb(teams))

@router.callback_query(F.data.startswith("eteam_"), CreateEvent.team)
async def create_event_team(callback: CallbackQuery, state: FSMContext):
    await state.update_data(team_id=int(callback.data.split("_")[1]))
    await state.set_state(CreateEvent.title)
    await callback.message.edit_text("✏️ Название события:", reply_markup=cancel_kb("admin_menu"))

@router.message(CreateEvent.title)
async def create_event_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateEvent.date)
    await message.answer("📅 Дата <b>ДД.ММ.ГГГГ</b>:", parse_mode="HTML")

@router.message(CreateEvent.date)
async def create_event_date(message: Message, state: FSMContext):
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        await state.update_data(event_date=d.strftime("%Y-%m-%d"))
        await state.set_state(CreateEvent.time)
        await message.answer("🕐 Время <b>ЧЧ:ММ</b>:", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Формат: <b>ДД.ММ.ГГГГ</b>", parse_mode="HTML")

@router.message(CreateEvent.time)
async def create_event_time(message: Message, state: FSMContext):
    import re
    if not re.match(r"^\d{2}:\d{2}$", message.text.strip()):
        await message.answer("❌ Формат: <b>ЧЧ:ММ</b>", parse_mode="HTML"); return
    await state.update_data(event_time=message.text.strip())
    await state.set_state(CreateEvent.location)
    await message.answer("📍 Место (или <b>-</b> пропустить):", parse_mode="HTML")

@router.message(CreateEvent.location)
async def create_event_location(message: Message, state: FSMContext):
    await state.update_data(location=None if message.text.strip() == "-" else message.text.strip())
    await state.set_state(CreateEvent.max_players)
    await message.answer("👥 Макс. игроков (по умолчанию 30, или введи число):")

@router.message(CreateEvent.max_players)
async def create_event_max(message: Message, state: FSMContext):
    try:
        mp = int(message.text.strip())
        if not 1 <= mp <= 100: raise ValueError
        await state.update_data(max_players=mp)
        await state.set_state(CreateEvent.description)
        await message.answer("📝 Описание (или <b>-</b> пропустить):", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Число от 1 до 100:")

@router.message(CreateEvent.description)
async def create_event_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = None if message.text.strip() == "-" else message.text.strip()

    event_id = await db.create_event(
        team_id=data["team_id"], type_=data["type"], title=data["title"],
        description=desc, event_date=data["event_date"], event_time=data["event_time"],
        location=data.get("location"), max_players=data["max_players"]
    )
    # Auto-register permanent players for trainings
    if data["type"] == "training":
        await db.auto_register_permanent_players(event_id, data["team_id"])

    tl = "🏋️ Тренировка" if data["type"] == "training" else "🏒 Игра/матч"
    await message.answer(
        f"✅ <b>Создано!</b>\n{tl}: <b>{data['title']}</b>\n"
        f"📅 {fmt_date(data['event_date'])} {data['event_time']}\n"
        f"👥 Мест: {data['max_players']}\n🆔 {event_id}",
        parse_mode="HTML", reply_markup=admin_menu_kb()
    )

# ── Monthly training creation ──────────────────────────────────────────

@router.callback_query(F.data == "create_monthly")
async def create_monthly_start(callback: CallbackQuery):
    if not await admin_required(callback): return
    teams = await db.get_teams()
    if not teams:
        await callback.message.edit_text("❌ Сначала создай команду.", reply_markup=admin_menu_kb()); return
    await callback.message.edit_text("👥 Выбери команду для создания тренировок на месяц:",
                                     reply_markup=teams_for_monthly_kb(teams))

@router.callback_query(F.data.startswith("monthly_team_"))
async def create_monthly_pick_month(callback: CallbackQuery):
    if not await admin_required(callback): return
    team_id = int(callback.data.split("_")[2])
    await callback.message.edit_text("📅 Выбери месяц:", reply_markup=month_select_kb(team_id))

@router.callback_query(F.data.startswith("monthly_create_"))
async def create_monthly_execute(callback: CallbackQuery):
    if not await admin_required(callback): return
    parts = callback.data.split("_")
    team_id, year, month = int(parts[2]), int(parts[3]), int(parts[4])

    await callback.message.edit_text("⏳ Создаю тренировки...")
    created = await db.create_monthly_trainings(team_id, year, month)

    # Auto-register permanent players for each created training
    for event_id, *_ in created:
        await db.auto_register_permanent_players(event_id, team_id)

    month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    team = await db.get_team(team_id)

    lines = [f"📅 {d.strftime('%d.%m')} ({['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][d.weekday()]}) {t} — {loc}"
             for _, d, t, loc in created]

    await callback.message.edit_text(
        f"✅ <b>Создано {len(created)} тренировок</b>\n"
        f"👥 {team['name']} · {month_names[month]} {year}\n\n" + "\n".join(lines),
        parse_mode="HTML", reply_markup=admin_menu_kb()
    )

# ── View events ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_events")
async def admin_events(callback: CallbackQuery):
    if not await admin_required(callback): return
    events = await db.get_upcoming_events()
    if not events:
        await callback.message.edit_text("📅 Нет событий.", reply_markup=admin_menu_kb()); return
    await callback.message.edit_text("📅 <b>Предстоящие события:</b>", parse_mode="HTML",
                                     reply_markup=events_admin_list_kb(events))

@router.callback_query(F.data.startswith("admin_event_"))
async def admin_event_detail(callback: CallbackQuery):
    if not await admin_required(callback): return
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    regs = await db.get_event_registrations(event_id)

    confirmed_list = "\n".join(
        [f"  {i+1}. {r['full_name']}" + (f" (@{r['username']})" if r['username'] else "")
         for i, r in enumerate(regs["confirmed"])]
    ) or "  —"
    waitlist_list = "\n".join(
        [f"  {i+1}. {r['full_name']}" for i, r in enumerate(regs["waitlist"])]
    ) or "  —"

    text = (
        f"{type_icon(event['type'])} <b>{event['title']}</b>\n"
        f"👥 {event['team_name']} · 📅 {fmt_date(event['event_date'])} {event['event_time']}\n"
        f"📍 {event['location'] or '—'}\n\n"
        f"✅ Записаны ({event['confirmed_count']}/{event['max_players']}):\n{confirmed_list}\n\n"
        f"⏳ Лист ожидания ({event['waitlist_count']}):\n{waitlist_list}"
    )
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=event_detail_admin_kb(event_id))

# ── Cancel / Delete event ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_event_"))
async def cancel_event_action(callback: CallbackQuery):
    if not await admin_required(callback): return
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    user_ids = await db.get_all_registered_user_ids(event_id)
    await db.cancel_event(event_id)

    notified = 0
    for uid in user_ids:
        try:
            await callback.bot.send_message(uid,
                f"❌ <b>Событие отменено!</b>\n\n{type_icon(event['type'])} {event['title']}\n"
                f"📅 {fmt_date(event['event_date'])} {event['event_time']}\n👥 {event['team_name']}",
                parse_mode="HTML")
            notified += 1
        except TelegramForbiddenError:
            pass

    await callback.message.edit_text(
        f"✅ Событие отменено. Уведомлено: {notified} игроков.",
        reply_markup=admin_menu_kb()
    )

@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_action(callback: CallbackQuery):
    if not await admin_required(callback): return
    event_id = int(callback.data.split("_")[2])
    await db.delete_event(event_id)
    await callback.message.edit_text("🗑 Событие удалено из базы.", reply_markup=admin_menu_kb())

# ── Remove player from event ───────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_regs_"))
async def admin_view_registrations(callback: CallbackQuery):
    if not await admin_required(callback): return
    event_id = int(callback.data.split("_")[2])
    event = await db.get_event(event_id)
    regs = await db.get_event_registrations(event_id)
    all_regs = list(regs["confirmed"]) + list(regs["waitlist"])

    if not all_regs:
        await callback.answer("Нет записей.", show_alert=True); return

    await callback.message.edit_text(
        f"👥 Записи на <b>{event['title']}</b>\nНажми на игрока чтобы удалить его запись:",
        parse_mode="HTML",
        reply_markup=registrations_list_kb(event_id, all_regs)
    )

@router.callback_query(F.data.startswith("remove_reg_"))
async def remove_player_registration(callback: CallbackQuery):
    if not await admin_required(callback): return
    parts = callback.data.split("_")
    event_id, user_id = int(parts[2]), int(parts[3])
    await db.remove_registration_by_admin(event_id, user_id)
    await callback.answer("✅ Запись удалена.", show_alert=True)
    # Refresh
    callback.data = f"admin_regs_{event_id}"
    await admin_view_registrations(callback)

# ── Permanent players ──────────────────────────────────────────────────

@router.callback_query(F.data == "permanent_players")
async def permanent_players_menu(callback: CallbackQuery):
    if not await admin_required(callback): return
    teams = await db.get_teams()
    if not teams:
        await callback.message.edit_text("❌ Нет команд.", reply_markup=admin_menu_kb()); return
    await callback.message.edit_text("👥 Выбери команду для управления постоянными игроками:",
                                     reply_markup=teams_for_monthly_kb(teams, prefix="perm_team"))

@router.callback_query(F.data.startswith("perm_team_"))
async def permanent_players_list(callback: CallbackQuery):
    if not await admin_required(callback): return
    team_id = int(callback.data.split("_")[2])
    team = await db.get_team(team_id)
    players = await db.get_permanent_players(team_id)

    text = f"👥 <b>Постоянные игроки: {team['name']}</b>\n\n"
    if players:
        text += "Нажми на игрока чтобы удалить:\n"
    else:
        text += "Список пуст."

    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=permanent_players_kb(team_id, players))

@router.callback_query(F.data.startswith("add_perm_"))
async def add_permanent_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_required(callback): return
    team_id = int(callback.data.split("_")[2])
    await state.update_data(team_id=team_id)
    await state.set_state(AddPermanentPlayer.name)
    await callback.message.edit_text(
        "✏️ Введи <b>Имя Фамилию</b> игрока:\n\n"
        "Если игрок уже зарегистрирован в боте, он будет автоматически привязан при следующей тренировке.",
        parse_mode="HTML", reply_markup=cancel_kb(f"perm_team_{team_id}")
    )

@router.message(AddPermanentPlayer.name)
async def add_permanent_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("❌ Введи Имя и Фамилию:"); return

    await db.add_permanent_player(data["team_id"], full_name)
    await state.clear()
    players = await db.get_permanent_players(data["team_id"])
    team = await db.get_team(data["team_id"])
    await message.answer(
        f"✅ <b>{full_name}</b> добавлен в постоянный список команды <b>{team['name']}</b>",
        parse_mode="HTML",
        reply_markup=permanent_players_kb(data["team_id"], players)
    )

@router.callback_query(F.data.startswith("del_perm_"))
async def delete_permanent_player(callback: CallbackQuery):
    if not await admin_required(callback): return
    parts = callback.data.split("_")
    player_id, team_id = int(parts[2]), int(parts[3])
    await db.remove_permanent_player(player_id)
    await callback.answer("Игрок удалён из постоянного списка.", show_alert=True)
    players = await db.get_permanent_players(team_id)
    team = await db.get_team(team_id)
    await callback.message.edit_text(
        f"👥 <b>Постоянные игроки: {team['name']}</b>\n\nНажми на игрока чтобы удалить:",
        parse_mode="HTML",
        reply_markup=permanent_players_kb(team_id, players)
    )

# ── Add admin ──────────────────────────────────────────────────────────

@router.message(Command("addadmin"))
async def add_admin_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID and not await db.is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав."); return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /addadmin <user_id>"); return
    try:
        uid = int(args[1])
        await db.add_admin(uid, None, f"Admin {uid}")
        await message.answer(f"✅ Пользователь {uid} теперь администратор.")
    except ValueError:
        await message.answer("❌ Неверный user_id.")
