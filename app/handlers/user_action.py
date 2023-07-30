from typing import List, Tuple

from aiogram import types
from aiogram.utils.markdown import hlink
from db.db_operations import RegisterDB
from handlers.internal_logic.register import internal_register_photo
from utils.TelegramUserClass import (
    Document,
    Photo,
    TelegramChat,
    TelegramDeserialize,
    TelegramUser,
)


async def register_photo(message: types.Message, register_unit: RegisterDB, msg: dict):
    if (
        message.from_user is None
        or message.chat.type == "private"
        or not message.caption
    ):
        return

    user, chat = TelegramDeserialize.unpack(message)
    theme = await register_unit.get_contest_theme(chat.telegram_id)
    if not theme:
        return
    vote_in_progress = await register_unit.get_current_vote_status(chat.telegram_id)
    if vote_in_progress:
        return

    valid_check = await is_valid_input(message.caption, theme, chat, user)
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


def strip_punctuation(s: str) -> str:
    if s[-1].isalnum():
        print(s)
        return s
    else:
        return strip_punctuation(s[:-1])


async def is_valid_input(
    caption: str,
    theme: str,
    chat_object: TelegramChat,
    user_object: TelegramUser,
) -> bool:

    message_search = caption.lower().split()
    message_contains_contest = False
    for word in message_search:
        if word.startswith(theme) and strip_punctuation(word) == theme:
            message_contains_contest = True
            break
    if message_contains_contest is not True:
        return False
    if not (
        (user_object and user_object.telegram_id)
        and chat_object
        and chat_object.telegram_id
    ):
        return False
    else:
        return True


def generate_board_message(template: str, user_list: List[Tuple[str, int]]):
    txt = ''
    if not user_list:
        txt = "Пока нет данных."
    for place, user_data in enumerate(user_list, start=1):
        user, total = user_data
        txt += template.format(
            place=place, link=hlink(user, f'https://t.me/{user}'), total=total,
        )
    return txt


async def view_leaders(message: types.Message, register_unit: RegisterDB):
    if message.chat.type == "private":
        return
    leader_list = await register_unit.select_winner_leaderboard(message.chat.id)
    template = "<b>{place}</b>: {link}, количество побед: {total}\n"
    await message.reply(
        generate_board_message(template, leader_list),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def view_overall_participants(message: types.Message, register_unit: RegisterDB):
    if message.chat.type == "private":
        return
    participants_list = await register_unit.select_participants_table(message.chat.id)
    template = "<b>{place}</b>: {link}, количество участий в челлендже {total}\n"
    await message.reply(
        generate_board_message(template, participants_list),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
