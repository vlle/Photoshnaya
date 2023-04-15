from aiogram import types
from sqlalchemy import Engine
from db.db_operations import get_contest_theme
from utils.TelegramUserClass import Photo, TelegramChat, TelegramUser
from handlers.internal_logic.register import _register_photo

async def register_photo(message: types.Message, engine: Engine):
    if message.from_user is None:
        return
    user = TelegramUser(message.from_user.username, message.from_user.full_name, message.from_user.id, message.chat.id, message.message_id)
    chat = TelegramChat(message.chat.username, message.chat.full_name, message.chat.id, message.message_id)
    valid_check = is_valid_input(message.caption, engine, chat, user)
    if valid_check is False:
        return

    if message.photo:
        photo = Photo(message.photo[-1].file_id)
        ret_msg = _register_photo(user, chat, engine, photo)
        await message.answer(ret_msg)



def is_valid_input(caption: str | None, engine: Engine, chat_object: TelegramChat, user_object: TelegramUser) -> bool:
    if not caption:
        return False
    theme = get_contest_theme(engine, chat_object.telegram_id)
    message_search = caption.split()
    message_contains_contest = False
    for word in message_search:
        if (word == theme):
            message_contains_contest = True
            break
    if (message_contains_contest is not True or not ((user_object and user_object.telegram_id) and chat_object and chat_object.telegram_id)):
        return False
    else:
        return True
