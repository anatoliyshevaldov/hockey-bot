from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать событие", callback_data="create_event")
    builder.button(text="📅 События", callback_data="admin_events")
    builder.button(text="🏒 Команды", callback_data="manage_teams")
    builder.adjust(1)
    return builder.as_markup()

def teams_list_kb(teams) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for team in teams:
        builder.button(text=f"🏒 {team['name']}", callback_data=f"delete_team_{team['id']}")
    builder.button(text="➕ Добавить команду", callback_data="add_team")
    builder.button(text="◀️ Назад", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def event_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏋️ Тренировка", callback_data="etype_training")
    builder.button(text="🏒 Игра/матч", callback_data="etype_game")
    builder.button(text="◀️ Отмена", callback_data="admin_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def teams_for_event_kb(teams) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for team in teams:
        builder.button(text=f"🏒 {team['name']}", callback_data=f"eteam_{team['id']}")
    builder.button(text="◀️ Отмена", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def cancel_kb(back_to: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Отмена", callback_data=back_to)
    return builder.as_markup()

def events_admin_list_kb(events) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for e in events:
        date_str = datetime.strptime(e["event_date"], "%Y-%m-%d").strftime("%d.%m")
        icon = "🏋️" if e["type"] == "training" else "🏒"
        builder.button(
            text=f"{icon} {e['title']} · {date_str} · {e['team_name']}",
            callback_data=f"admin_event_{e['id']}"
        )
    builder.button(text="◀️ Назад", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def event_detail_kb(event_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить событие", callback_data=f"cancel_event_{event_id}")
    builder.button(text="◀️ Назад", callback_data="admin_events")
    builder.adjust(1)
    return builder.as_markup()
