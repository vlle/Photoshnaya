from aiogram import types
from aiogram import Bot
from sqlalchemy import Engine
from utils.TelegramUserClass import TelegramDeserialize
from handlers.internal_logic.admin import i_set_theme
from handlers.internal_logic.on_join import i_on_user_join
from db.db_operations import Register, check_admin, get_contest_theme


async def set_theme(message: types.Message, bot: Bot, engine: Engine):
    if not message.text or not message.from_user:
        return
    user, chat = TelegramDeserialize.unpack(message)
    admin_right = check_admin(engine, user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return

    user_theme = message.text.split()
    msg = i_set_theme(user_theme, engine, user, chat)
    await bot.send_message(message.chat.id, msg)


async def get_theme(message: types.Message, bot: Bot, engine: Engine):
    if not message.text or not message.from_user:
        return
    user, chat = TelegramDeserialize.unpack(message)
    admin_right = check_admin(engine, user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return

    theme = get_contest_theme(engine, chat.telegram_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


async def on_user_join(message: types.Message, bot: Bot, register_unit: Register):
    user, chat = TelegramDeserialize.unpack(message, message_id_not_exists=True)

    msg, reg_msg = i_on_user_join(register_unit=register_unit, user=user, chat=chat)

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
