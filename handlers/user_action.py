from aiogram import types
from aiogram import Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from utils.keyboard import Keyboard, Actions, CallbackVote
from sqlalchemy import Engine
from db.db_operations import get_contest_theme, build_user, build_group, register_user, set_register_photo

async def register_photo(message: types.Message, engine: Engine):
    if not message.caption:
        return
    theme = get_contest_theme(engine, str(message.chat.id))
    message_search = message.caption.split()
    message_contains_contest = False
    for word in message_search:
        if (word == theme):
            message_contains_contest = True
            break
    if (message_contains_contest is not True or not (message.from_user and message.from_user.id
        and message.chat and message.chat.id)):
        return

    user = build_user(str(message.from_user.username),
                      message.from_user.full_name,
                      str(message.from_user.id))
    group = build_group(message.chat.full_name,
                        str(message.chat.id),
                        "none")
    ret = register_user(engine, user, str(message.chat.id))
    await message.answer(ret + str(message.chat.id))
    if message.photo:
        file_id = message.photo[-1].file_id
        set_register_photo(engine, str(message.from_user.id),
                           str(message.chat.id), file_get_id=file_id, user_p=user, group_p=group)
    else:
        set_register_photo(engine, str(message.from_user.id),
                           str(message.chat.id), file_get_id='-1', user_p=user, group_p=group)
    await message.answer(f"Зарегал фотку! Тема: {theme} ")



