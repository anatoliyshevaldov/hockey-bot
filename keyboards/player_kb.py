from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="🎯 Мои записи")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

def teams_list_kb(teams) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for team in teams:
        builder.button(text=f"🏒 {team['name']}", callback_data=f"team_events_{team['id']}")
    builder.adjust(1)
    return builder.as_markup()

def events_list_kb(events, team_id) -> InlineKeyboardMarkup:
    from datetime import datetime
    builder = InlineKeyboardBuilder()
    for e in events:
        date_str = datetime.strptime(e["event_date"], "%Y-%m-%d").strftime("%d.%m")
        icon = "🏋️" if e["type"] == "training" else "🏒"
        spots = f"{e['confirmed_count']}/{e['max_players']}"
        builder.button(
            text=f"{icon} {e['title']} · {date_str} · {spots}",
            callback_data=f"event_detail_{e['id']}"
        )
    builder.button(text="◀️ Назад", callback_data="back_to_teams")
    builder.adjust(1)
    return builder.as_markup()

def event_detail_kb(event_id: int, team_id: int, user_reg=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if user_reg is None:
        builder.button(text="✅ Записаться", callback_data=f"register_{event_id}")
    elif user_reg["status"] == "confirmed":
        builder.button(text="❌ Отменить запись", callback_data=f"cancel_reg_{event_id}")
    elif user_reg["status"] == "waitlist":
        builder.button(text="❌ Выйти из листа ожидания", callback_data=f"cancel_reg_{event_id}")
    builder.button(text="◀️ Назад", callback_data=f"team_events_{team_id}")
    builder.adjust(1)
    return builder.as_markup()

def my_events_kb(events) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for e in events:
        from datetime import datetime
        date_str = datetime.strptime(e["event_date"], "%Y-%m-%d").strftime("%d.%m")
        icon = "🏋️" if e["type"] == "training" else "🏒"
        status = "✅" if e["reg_status"] == "confirmed" else "⏳"
        builder.button(
            text=f"{status} {icon} {e['title']} · {date_str}",
            callback_data=f"myevent_{e['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()
