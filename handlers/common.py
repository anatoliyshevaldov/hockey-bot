from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from keyboards.player_kb import main_menu_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_adm = await db.is_admin(message.from_user.id)

    text = (
        f"🏒 <b>Добро пожаловать в хоккейный бот!</b>\n\n"
        f"Здесь можно записаться на тренировки и игры своей команды.\n\n"
    )
    if is_adm:
        text += "👑 <b>Ты администратор.</b> Используй /admin для управления.\n\n"

    text += "Выбери действие:"
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())

@router.message(Command("help"))
async def cmd_help(message: Message):
    is_adm = await db.is_admin(message.from_user.id)
    text = (
        "📋 <b>Доступные команды:</b>\n\n"
        "/start — главное меню\n"
        "/schedule — расписание событий\n"
        "/myevents — мои записи\n"
        "/help — эта справка\n"
    )
    if is_adm:
        text += (
            "\n👑 <b>Команды администратора:</b>\n"
            "/admin — панель управления\n"
            "/addadmin &lt;user_id&gt; — добавить администратора\n"
        )
    await message.answer(text, parse_mode="HTML")
