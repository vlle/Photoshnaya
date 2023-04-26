from typing import Any
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram import Bot
from utils.admin_keyboard import AdminKeyboard, CallbackManage
from db.db_operations import AdminDB
from handlers.internal_logic.admin import i_set_theme

class ContestCreate(StatesGroup):
    name_contest = State()
    are_you_sure = State()
    thanks_for_info = State()

async def set_theme(query: types.CallbackQuery, 
                    callback_data: CallbackManage, 
                    state: FSMContext,
                    msg: dict):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(text=msg["contest"]["create_greet_contest"])
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    await state.set_data(data)
    await state.set_state(ContestCreate.name_contest)

async def set_theme_accept_message(message: types.Message, bot: Bot,
                                   state: FSMContext, admin_unit: AdminDB,
                                   msg: dict):
    if not message.text:
        return
    theme = message.text.split()
    string: dict[str, Any] = await state.get_data()
    keyboard = string["keyboard"]
    if (len(theme) > 1 or theme[0].lower() == 'отмена' 
            or theme[0].lower() == 'cancel'):
        text = msg["contest"]["cancel_contest"]
    else:
        text = await i_set_theme(theme[0], admin_unit, int(
            string["group"]))

    await state.clear()
    await bot.edit_message_text(text=text,
                                 chat_id=string["user_id"],
                                 message_id=string["msg_id"],
                                 reply_markup=keyboard.keyboard_back)



