import pathlib
import tomllib

from sqlalchemy.exc import SQLAlchemyError

from db.db_operations import LikeDB, VoteDB
from utils.TelegramUserClass import TelegramChat, TelegramUser


async def internal_start(
    chat: TelegramChat, user: TelegramUser, text: str, like_engine: LikeDB
) -> tuple:
    text_toml = pathlib.Path(__file__).absolute().parent.parent / 'handlers_text' / 'text.toml'
    with open(text_toml, "rb") as f:
        msg = tomllib.load(f)
    start_data = text.replace("_", " ").split()
    if len(start_data) != 3:
        return msg["vote"]["wrong_link"], True, None
    if chat.chat_type != "private":
        return msg["vote"]["not_private_chat"], True, None
    group_id = int(start_data[1])
    try:
        photo_ids = await like_engine.select_contest_photos_ids(group_id)
        if len(photo_ids) == 0:
            return msg["vote"]["no_photos"], True, None
    except SQLAlchemyError:
        return msg["vote"]["unexpected_error"], True, None

    vote_db = VoteDB(like_engine.engine)

    if await vote_db.get_current_vote_status(group_id) is False:
        return msg["vote"]["no_vote_yet"], True, None

    if await vote_db.is_user_not_allowed_to_vote(group_id, user.telegram_id) is True:
        return msg["vote"]["already_voted"], True, None

    return msg["vote"]["greeting_message_vote"], False, photo_ids
