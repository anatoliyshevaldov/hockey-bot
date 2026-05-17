from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards.player_kb import main_menu_kb

router = Router()

class Registration(StatesGroup):
    full_name = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)

    if not user or not user["full_name"]:
        await state.set_state(Registration.full_name)
        await message.answer(
            "🏒 <b>Добро пожаловать в хоккейный бот!</b>\n\n"
            "Для записи на тренировки и игры нужно представиться.\n\n"
            "Введи своё <b>Имя и Фамилию</b>:",
            parse_mode="HTML"
        )
        return

    await show_main_menu(message, user["full_name"])

@router.message(Registration.full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введи и <b>Имя</b> и <b>Фамилию</b> через пробел:", parse_mode="HTML")
        return

    await db.save_user(message.from_user.id, message.from_user.username, full_name)
    await state.clear()

    is_adm = await db.is_admin(message.from_user.id)
    text = f"✅ Отлично, <b>{full_name}</b>! Ты зарегистрирован.\n\n"
    if is_adm:
        text += "👑 У тебя есть права администратора. Используй /admin\n\n"
    text += "Выбери действие:"
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())

async def show_main_menu(message: Message, full_name: str = None):
    is_adm = await db.is_admin(message.from_user.id)
    text = f"👋 Привет, <b>{full_name}</b>!\n\n" if full_name else "🏒 Главное меню\n\n"
    if is_adm:
        text += "👑 Ты администратор. /admin\n\n"
    text += "Выбери действие:"
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())

@router.message(Command("help"))
async def cmd_help(message: Message):
    is_adm = await db.is_admin(message.from_user.id)
    text = (
        "📋 <b>Команды:</b>\n\n"
        "/start — главное меню\n"
        "/schedule — расписание тренировок\n"
        "/games — расписание игр\n"
        "/myevents — мои записи\n"
        "/help — справка\n"
    )
    if is_adm:
        text += "\n👑 <b>Администратор:</b>\n/admin — панель управления\n/addadmin &lt;id&gt; — добавить админа\n"
    await message.answer(text, parse_mode="HTML")
