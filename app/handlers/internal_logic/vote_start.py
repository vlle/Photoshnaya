import pathlib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from services.vote_backend import VoteBackend, VoteBackendBusinessError
from utils.TelegramUserClass import TelegramChat, TelegramUser


async def internal_start(
    chat: TelegramChat, user: TelegramUser, text: str, like_engine: VoteBackend
) -> tuple:
    text_toml = pathlib.Path(__file__).absolute().parent.parent / 'handlers_text' / 'text.toml'
    with open(text_toml, "rb") as f:
        msg = tomllib.load(f)
    start_data = text.replace("_", " ").split()
    if len(start_data) != 3:
        return msg["vote"]["wrong_link"], True, None
    if chat.chat_type != "private":
        return msg["vote"]["not_private_chat"], True, None
    try:
        group_id = int(start_data[1])
    except ValueError:
        return msg["vote"]["wrong_link"], True, None
    try:
        vote_session = await like_engine.get_vote_session(group_id, user.telegram_id)
    except VoteBackendBusinessError as err:
        if err.code == "no_photos":
            return msg["vote"]["no_photos"], True, None
        if err.code == "no_vote_yet":
            return msg["vote"]["no_vote_yet"], True, None
        if err.code == "already_voted":
            return msg["vote"]["already_voted"], True, None
        return msg["vote"]["unexpected_error"], True, None
    except Exception:
        return msg["vote"]["unexpected_error"], True, None

    return msg["vote"]["greeting_message_vote"], False, vote_session
