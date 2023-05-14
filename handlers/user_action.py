from aiogram import types
from db.db_operations import RegisterDB
from utils.TelegramUserClass import Photo, TelegramChat,\
            TelegramDeserialize, TelegramUser, Document
from handlers.internal_logic.register import internal_register_photo


async def register_photo(message: types.Message, register_unit: RegisterDB, msg: dict):
    if message.from_user is None or message.chat.type =='private':
        return
    user, chat = TelegramDeserialize.unpack(message)
    valid_check = await is_valid_input(message.caption, register_unit, chat, user)
    if valid_check is False:
        return

    if message.photo:
        obj = Photo(message.photo[-1].file_id)
    elif message.document:
        obj = Document(message.document.file_id)
    else:
        return
    ret_msg = await internal_register_photo(user, chat, register_unit, obj, msg)
    await message.reply(ret_msg)


async def is_valid_input(caption: str | None,
                   register: RegisterDB,
                   chat_object: TelegramChat,
                   user_object: TelegramUser) -> bool:
    if not caption:
        return False
    theme = await register.get_contest_theme(chat_object.telegram_id)
    if not theme:
        return False

    message_search = caption.lower().split()
    message_contains_contest = False
    for word in message_search:
        if (word == theme):
            message_contains_contest = True
            break
    if message_contains_contest is not True:
        return False
    if not ((user_object and user_object.telegram_id) and
            chat_object and chat_object.telegram_id):
        return False
    else:
        return True


async def view_leaders(message: types.Message, register_unit: RegisterDB):
    if message.chat.type == 'private':
        return
    leader_list = await register_unit.select_winner_leaderboard(message.chat.id)
    txt = ''
    i = 1
    for leader in leader_list:
        txt += f"<b>{i}:</b> @{leader[0]}, количество побед: {leader[1]}\n"
        i += 1
    if i == 1:
        txt = "Пока нет данных"
    await message.reply(txt, parse_mode="HTML")


async def view_overall_participants(message: types.Message, register_unit: RegisterDB):
    if message.chat.type == 'private':
        return
    leader_list = await register_unit.select_participants_table(message.chat.id)
    txt = ''
    i = 1
    for leader in leader_list:
        txt += f"<b>{i}:</b> @{leader[0]} и количество участий в челлендже: {leader[1]}\n"
        i += 1
    if i == 1:
        txt = "Пока нет данных"
    await message.reply(txt, parse_mode="HTML")
