from typing import Any

from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.db_operations import AdminDB
from handlers.internal_logic.del_admin import i_del_admin
from utils.admin_keyboard import AdminKeyboard, CallbackManage
from utils.TelegramUserClass import TelegramUser


class AdminDel(StatesGroup):
    send_admin = State()
    are_you_sure = State()
    thanks_for_info = State()


async def del_admin(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    state: FSMContext,
    msg: dict,
):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(
        text=msg["del_admin"]["delete_greet_adm"], parse_mode="HTML"
    )
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    await state.set_data(data)
    await state.set_state(AdminDel.send_admin)


async def del_admin_accept_message(
    message: types.Message, bot: Bot, state: FSMContext, admin_unit: AdminDB, msg: dict
):
    if not message.text:
        return
    theme = message.text.split()
    string: dict[str, Any] = await state.get_data()
    keyboard = string["keyboard"]
    if (
        not message.forward_from
        or len(theme) > 1
        or theme[0].lower() == "отмена"
        or theme[0].lower() == "cancel"
    ):
        text = msg["del_admin"]["cancel_adm"]
    else:
        user = TelegramUser(
            message.forward_from.username,
            message.forward_from.full_name,
            message.forward_from.id,
            message_id=message.message_id,
            chat_id=int(string["group"]),
        )
        text = await i_del_admin(user_object=user, register=admin_unit, msg=msg)

    await state.clear()
    await bot.edit_message_text(
        text=text,
        chat_id=string["user_id"],
        message_id=string["msg_id"],
        reply_markup=keyboard.keyboard_back,
    )
