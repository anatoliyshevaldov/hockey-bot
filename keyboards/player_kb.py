from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

def fmt_date(s): return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m")

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏋️ Тренировки"), KeyboardButton(text="🏒 Игры")],
            [KeyboardButton(text="🎯 Мои записи"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

def teams_list_kb(teams, prefix="team_tr") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in teams:
        b.button(text=f"🏒 {t['name']}", callback_data=f"{prefix}_{t['id']}")
    b.adjust(1)
    return b.as_markup()

def events_list_kb(events, back_cb) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in events:
        icon = "🏋️" if e["type"] == "training" else "🏒"
        spots = f"{e['confirmed_count']}/{e['max_players']}"
        b.button(
            text=f"{icon} {e['title']} · {fmt_date(e['event_date'])} · {spots}",
            callback_data=f"event_detail_{e['id']}"
        )
    b.button(text="◀️ Назад", callback_data=back_cb)
    b.adjust(1)
    return b.as_markup()

def event_detail_kb(event_id: int, back_cb: str, user_reg=None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if user_reg is None:
        b.button(text="✅ Записаться", callback_data=f"register_{event_id}")
    elif user_reg["status"] == "confirmed":
        b.button(text="❌ Отменить запись", callback_data=f"cancel_reg_{event_id}")
    elif user_reg["status"] == "waitlist":
        b.button(text="❌ Выйти из листа ожидания", callback_data=f"cancel_reg_{event_id}")
    b.button(text="◀️ Назад", callback_data=back_cb)
    b.adjust(1)
    return b.as_markup()

def my_events_kb(events) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in events:
        icon = "🏋️" if e["type"] == "training" else "🏒"
        st = "✅" if e["reg_status"] == "confirmed" else "⏳"
        b.button(
            text=f"{st} {icon} {e['title']} · {fmt_date(e['event_date'])} — ❌ отменить",
            callback_data=f"myevent_cancel_{e['id']}"
        )
    b.adjust(1)
    return b.as_markup()
