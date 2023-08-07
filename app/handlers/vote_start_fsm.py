from typing import Any

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.db_operations import AdminDB, ObjectFactory
from utils.admin_keyboard import AdminKeyboard, CallbackManage

# from utils.logger import logger | not working correctly


class VoteStart(StatesGroup):
    vote_text = State()
    are_you_sure = State()
    will_you_post = State()
    thanks_for_info = State()


async def set_vote(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    state: FSMContext,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
    bot: Bot,
):
    if not query.message:
        query.answer("Слишком старое сообщение, запусти новое")
        return
    keyboard: AdminKeyboard = AdminKeyboard.fromcallback(callback_data)
    bot_t = await bot.me()
    if not bot_t.username:
        await query.message.edit_text(
            text=msg["vote"]["no_username_bot"], reply_markup=keyboard.keyboard_back
        )
        return

    bot_link = ObjectFactory.build_vote_link(bot_t.username, callback_data.group_id)
    theme = await admin_unit.get_contest_theme(int(callback_data.group_id))
    photos = await admin_unit.select_contest_photos_ids(int(callback_data.group_id))
    amount_photo = len(photos)
    vote_announce = msg["vote"]["start_vote"].format(
        theme=theme,
        amount_photo=amount_photo,
        link=bot_link,
        str_date="завтра вечером",
    )
    await query.message.edit_text(
        text=msg["vote"]["will_you_post"] + vote_announce, parse_mode="HTML"
    )
    await admin_unit.change_current_vote_status(int(callback_data.group_id))
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    data["text"] = vote_announce
    await state.set_data(data)
    await state.set_state(VoteStart.will_you_post)


async def should_i_post_vote(
    message: types.Message, bot: Bot, state: FSMContext, msg: dict
):
    data: dict[str, Any] = await state.get_data()
    ret_text = data["text"]
    if message.text and (message.text.lower() == "ок" or message.text.lower() == "ok"):
        message_to_pin = await bot.send_message(
            chat_id=data["group"], text=ret_text, parse_mode="HTML"
        )
        try:
            await bot.pin_chat_message(
                chat_id=data["group"], message_id=message_to_pin.message_id
            )
        except TelegramBadRequest:
            # logger.error(msg["contest"]["err"], exc_info=True)
            await bot.send_message(chat_id=data["group"], text=msg["contest"]["err"])
        await state.clear()
    else:
        data["text"] = message.html_text
        await state.set_data(data)
        bots_text = msg["contest"]["will_you_post"] + message.html_text
        await bot.edit_message_text(
            text=bots_text,
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            parse_mode="HTML",
        )
        await state.set_state(VoteStart.will_you_post)
