import logging
import os
from typing import Any, List, Tuple

from aiogram import types
from aiogram.utils.markdown import hlink
from aiohttp import ClientError, ClientSession, ClientTimeout
from db.db_operations import RegisterDB
from handlers.internal_logic.register import internal_register_photo
from utils.TelegramUserClass import (
    Document,
    Photo,
    TelegramChat,
    TelegramDeserialize,
    TelegramUser,
)

FEATURE_GO_LEADERBOARDS = "FEATURE_GO_LEADERBOARDS"
GO_BRIDGE_BASE_URL = "GO_BRIDGE_BASE_URL"
GO_BRIDGE_TIMEOUT_MS = "GO_BRIDGE_TIMEOUT_MS"


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


def _is_true_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_bridge_timeout() -> float:
    raw = os.environ.get(GO_BRIDGE_TIMEOUT_MS, "800")
    try:
        timeout_ms = int(raw)
    except ValueError:
        timeout_ms = 800
    if timeout_ms <= 0:
        timeout_ms = 800
    return timeout_ms / 1000


async def _delegate_winners_board(group_id: int) -> dict[str, Any] | None:
    if not _is_true_env(FEATURE_GO_LEADERBOARDS):
        return None

    bridge_base = os.environ.get(GO_BRIDGE_BASE_URL, "http://go-bot:8080").rstrip("/")
    request_url = f"{bridge_base}/internal/v1/leaderboards/winners"
    timeout = ClientTimeout(total=_get_bridge_timeout())

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.get(
                request_url, params={"group_telegram_id": str(group_id)}
            ) as response:
                if response.status != 200:
                    logging.warning(
                        "go leaderboard bridge returned non-200",
                        extra={"status": response.status, "group_id": group_id},
                    )
                    return None
                payload = await response.json()
    except (ClientError, TimeoutError, ValueError) as err:
        logging.warning(
            "go leaderboard bridge request failed",
            exc_info=err,
            extra={"group_id": group_id},
        )
        return None

    if not isinstance(payload, dict):
        return None

    text = payload.get("text")
    if not isinstance(text, str):
        return None

    parse_mode = payload.get("parse_mode")
    if not isinstance(parse_mode, str):
        parse_mode = "HTML"

    disable_preview = payload.get("disable_web_page_preview")
    if not isinstance(disable_preview, bool):
        disable_preview = True

    return {
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }


async def view_leaders(message: types.Message, register_unit: RegisterDB):
    if message.chat.type == "private":
        return
    delegated_payload = await _delegate_winners_board(message.chat.id)
    if delegated_payload is not None:
        await message.reply(
            delegated_payload["text"],
            parse_mode=delegated_payload["parse_mode"],
            disable_web_page_preview=delegated_payload["disable_web_page_preview"],
        )
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
