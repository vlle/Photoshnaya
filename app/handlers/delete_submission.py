from typing import Any

from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from db.db_operations import AdminDB
from utils.admin_keyboard import AdminKeyboard, CallbackManage
from utils.TelegramUserClass import TelegramUser


class DeletePhoto(StatesGroup):
    send_photo_owner = State()
    are_you_sure = State()
    wait_for_confirmation = State()


async def delete_submission(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    state: FSMContext,
    msg: dict,
):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(
        text=msg["delete_photo"]["create_greet_del"], parse_mode="HTML"
    )
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    await state.set_data(data)
    await state.set_state(DeletePhoto.send_photo_owner)


async def set_admin_delete_photo(
    message: types.Message, bot: Bot, state: FSMContext, admin_unit: AdminDB, msg: dict
):
    if not message.text:
        return
    theme = message.text.split()
    data: dict[str, Any] = await state.get_data()
    keyboard = data["keyboard"]
    if theme[0].lower() == "отмена" or theme[0].lower() == "cancel":
        text = msg["delete_photo"]["cancel_del"]
        await bot.edit_message_text(
            text=text,
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            reply_markup=keyboard.keyboard_back,
        )
    elif message.text.startswith("@") and not message.forward_from:
        possible_username = message.text[1:]
        user_data = await admin_unit.find_user_by_username_in_group(
            possible_username, int(data["group"])
        )
        if user_data:
            username, full_name, id = user_data[0], user_data[1], user_data[2]
            user = TelegramUser(
                username,
                full_name,
                id,
                message_id=message.message_id,
                chat_id=int(data["group"]),
            )
            data["forward"] = user
            await state.set_data(data)
            await delete_photo_r_u_sure(bot, state, admin_unit, msg)
        else:
            text = msg["delete_photo"]["no_user"]
            await bot.edit_message_text(
                text=text,
                chat_id=data["user_id"],
                message_id=data["msg_id"],
                reply_markup=keyboard.keyboard_back,
            )
            await state.clear()
    elif not message.forward_from:
        text = msg["delete_photo"]["no_user"]
        await bot.edit_message_text(
            text=text,
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            reply_markup=keyboard.keyboard_back,
        )
        await state.clear()
    else:
        user = TelegramUser(
            message.forward_from.username,
            message.forward_from.full_name,
            message.forward_from.id,
            message_id=message.message_id,
            chat_id=int(data["group"]),
        )
        data["forward"] = user
        await state.set_data(data)
        await delete_photo_r_u_sure(bot, state, admin_unit, msg)


async def delete_photo_r_u_sure(
    bot: Bot, state: FSMContext, admin_unit: AdminDB, msg: dict[str, dict[str, str]]
):
    data: dict[str, Any] = await state.get_data()
    user: TelegramUser = data["forward"]
    author = f"{user.username}, {user.full_name}"
    text = msg["delete_photo"]["are_you_sure"].format(author=author)
    keyboard = data["keyboard"]
    photo_data = await admin_unit.find_photo_by_user_in_group(
        user.telegram_id, int(data["group"])
    )
    if photo_data is None:
        text = "Не нашел фото от пользователя.\n" + msg["add_admin"]["cancel_adm"]
        await bot.edit_message_text(
            text=text,
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            reply_markup=keyboard.keyboard_back,
        )
        await state.clear()
        return
    photo_file_id = photo_data[1]
    photo_type = photo_data[2]
    data["photo_del"] = photo_data
    await state.set_data(data)

    reply_board = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Да")], [types.KeyboardButton(text="Нет")]]
    )
    if photo_type == "photo":
        await bot.send_photo(
            data["user_id"],
            caption=text,
            photo=photo_file_id,
            reply_markup=reply_board,
        )
    else:
        await bot.send_document(
            data["user_id"],
            caption=text,
            document=photo_file_id,
            reply_markup=reply_board,
        )
    await state.set_state(DeletePhoto.wait_for_confirmation)


async def make_delete_decision(
    message: types.Message, state: FSMContext, admin_unit: AdminDB, msg: dict
):
    if not message.text or message.text.lower() == "нет":
        await message.reply(
            text=msg["delete_photo"]["cancel_del"],
            reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
        )
        await state.clear()
    elif message.text.lower() == "да":
        data: dict[str, Any] = await state.get_data()
        photo_data = data["photo_del"]
        photo_file_id = photo_data[1]
        await admin_unit.remove_photo(photo_file_id)
        await message.reply(
            text=msg["delete_photo"]["del_photo"],
            reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
        )
    else:
        await message.reply(
            text=msg["delete_photo"]["no_understand"],
            reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
        )
        await state.clear()
