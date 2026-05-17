from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date

def fmt_date(s): return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m")

def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать событие", callback_data="create_event")
    b.button(text="📅 Тренировки на месяц", callback_data="create_monthly")
    b.button(text="📋 Все события", callback_data="admin_events")
    b.button(text="👥 Постоянные игроки", callback_data="permanent_players")
    b.button(text="🏒 Команды", callback_data="manage_teams")
    b.adjust(1)
    return b.as_markup()

def teams_list_kb(teams) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in teams:
        b.button(text=f"🗑 {t['name']}", callback_data=f"delete_team_{t['id']}")
    b.button(text="➕ Добавить команду", callback_data="add_team")
    b.button(text="◀️ Назад", callback_data="admin_menu")
    b.adjust(1)
    return b.as_markup()

def event_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏋️ Тренировка", callback_data="etype_training")
    b.button(text="🏒 Игра/матч", callback_data="etype_game")
    b.button(text="◀️ Отмена", callback_data="admin_menu")
    b.adjust(2, 1)
    return b.as_markup()

def teams_for_event_kb(teams) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in teams:
        b.button(text=f"🏒 {t['name']}", callback_data=f"eteam_{t['id']}")
    b.button(text="◀️ Отмена", callback_data="admin_menu")
    b.adjust(1)
    return b.as_markup()

def teams_for_monthly_kb(teams, prefix="monthly_team") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in teams:
        b.button(text=f"🏒 {t['name']}", callback_data=f"{prefix}_{t['id']}")
    b.button(text="◀️ Назад", callback_data="admin_menu")
    b.adjust(1)
    return b.as_markup()

def month_select_kb(team_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    for i in range(3):
        m = today.month + i
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        b.button(text=f"{month_names[m]} {y}", callback_data=f"monthly_create_{team_id}_{y}_{m}")
    b.button(text="◀️ Назад", callback_data="create_monthly")
    b.adjust(1)
    return b.as_markup()

def cancel_kb(back_to: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Отмена", callback_data=back_to)
    return b.as_markup()

def events_admin_list_kb(events) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in events:
        icon = "🏋️" if e["type"] == "training" else "🏒"
        b.button(
            text=f"{icon} {e['title']} · {fmt_date(e['event_date'])} · {e['team_name']} ({e['confirmed_count']}/{e['max_players']})",
            callback_data=f"admin_event_{e['id']}"
        )
    b.button(text="◀️ Назад", callback_data="admin_menu")
    b.adjust(1)
    return b.as_markup()

def event_detail_admin_kb(event_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👥 Управлять записями", callback_data=f"admin_regs_{event_id}")
    b.button(text="❌ Отменить (с уведомлением)", callback_data=f"cancel_event_{event_id}")
    b.button(text="🗑 Удалить из базы", callback_data=f"delete_event_{event_id}")
    b.button(text="◀️ Назад", callback_data="admin_events")
    b.adjust(1)
    return b.as_markup()

def registrations_list_kb(event_id: int, registrations) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in registrations:
        st = "✅" if r["status"] == "confirmed" else "⏳"
        b.button(
            text=f"{st} {r['full_name']} — удалить",
            callback_data=f"remove_reg_{event_id}_{r['user_id']}"
        )
    b.button(text="◀️ Назад", callback_data=f"admin_event_{event_id}")
    b.adjust(1)
    return b.as_markup()

def permanent_players_kb(team_id: int, players) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in players:
        b.button(text=f"🗑 {p['full_name']}", callback_data=f"del_perm_{p['id']}_{team_id}")
    b.button(text="➕ Добавить игрока", callback_data=f"add_perm_{team_id}")
    b.button(text="◀️ Назад", callback_data="permanent_players")
    b.adjust(1)
    return b.as_markup()
