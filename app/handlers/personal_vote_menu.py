import logging
import os
from typing import Any

from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InputMediaDocument, InputMediaPhoto
from aiohttp import ClientError, ClientSession, ClientTimeout

from db.db_operations import LikeDB, ObjectFactory, RegisterDB, VoteDB
from handlers.internal_logic.vote_start import internal_start
from utils.keyboard import CallbackVote, Keyboard
from utils.TelegramUserClass import TelegramDeserialize

PLACEHOLDER = "AgACAgIAAxkBAAIbk2SlfwGmaPoK776SSq0OYGaZwi6wAAJtyjEbMIUoSXnXybpELj9PAQADAgADeAADLwQ"

FEATURE_GO_VOTE_FLOW = "FEATURE_GO_VOTE_FLOW"
GO_BRIDGE_BASE_URL = "GO_BRIDGE_BASE_URL"
GO_BRIDGE_TIMEOUT_MS = "GO_BRIDGE_TIMEOUT_MS"

VOTE_START_PATH = "/internal/v1/vote/start"
VOTE_NEXT_PATH = "/internal/v1/vote/next"
VOTE_PREV_PATH = "/internal/v1/vote/prev"
VOTE_LIKE_PATH = "/internal/v1/vote/like"
VOTE_UNLIKE_PATH = "/internal/v1/vote/unlike"
VOTE_SUBMIT_PATH = "/internal/v1/vote/submit"


# debug function
async def get_file_id(message: types.Message):
    if not message.photo:
        return
    file_id = message.photo[-1].file_id
    await message.answer(file_id)


def _is_true_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _vote_bridge_enabled() -> bool:
    return _is_true_env(FEATURE_GO_VOTE_FLOW)


def _bridge_timeout_seconds() -> float:
    raw = os.environ.get(GO_BRIDGE_TIMEOUT_MS, "800")
    try:
        timeout_ms = int(raw)
    except ValueError:
        timeout_ms = 800
    if timeout_ms <= 0:
        timeout_ms = 800
    return timeout_ms / 1000


async def _call_vote_bridge(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _vote_bridge_enabled():
        return None

    base = os.environ.get(GO_BRIDGE_BASE_URL, "http://go-bot:8080").rstrip("/")
    timeout = ClientTimeout(total=_bridge_timeout_seconds())
    url = f"{base}{path}"

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    logging.warning(
                        "go vote bridge returned non-200",
                        extra={"status": response.status, "path": path},
                    )
                    return None
                data = await response.json()
    except (ClientError, TimeoutError, ValueError) as err:
        logging.warning(
            "go vote bridge request failed",
            exc_info=err,
            extra={"path": path},
        )
        return None

    if not isinstance(data, dict):
        return None
    return data


def _resolve_vote_text(msg: dict[str, Any], code: Any, default_key: str) -> str:
    vote_messages = msg.get("vote", {})
    if isinstance(vote_messages, dict):
        if isinstance(code, str) and code in vote_messages:
            value = vote_messages.get(code)
            if isinstance(value, str):
                return value
        default_value = vote_messages.get(default_key)
        if isinstance(default_value, str):
            return default_value
        fallback = vote_messages.get("unexpected_error")
        if isinstance(fallback, str):
            return fallback
    return "Произошла какая-то ошибка"


def _extract_vote_state(payload: dict[str, Any]) -> dict[str, Any] | None:
    state = payload.get("state")
    if not isinstance(state, dict):
        return None

    try:
        parsed: dict[str, Any] = {
            "group_id": int(state["group_id"]),
            "amount_photos": int(state["amount_photos"]),
            "current_photo_id": int(state["current_photo_id"]),
            "current_photo_count": int(state["current_photo_count"]),
            "is_liked_photo": int(state["is_liked_photo"]),
        }
    except (KeyError, TypeError, ValueError):
        return None

    media_type = state.get("media_type", "photo")
    if not isinstance(media_type, str) or media_type not in {"photo", "document"}:
        media_type = "photo"

    media_file_id = state.get("media_file_id", "")
    if not isinstance(media_file_id, str):
        media_file_id = ""

    parsed["media_type"] = media_type
    parsed["media_file_id"] = media_file_id
    return parsed


async def cmd_start(message: types.Message, bot: Bot, like_engine: LikeDB, msg: dict):
    if not message.text or not message.from_user:
        return

    user, chat = TelegramDeserialize.unpack(message)

    bridge_payload = await _call_vote_bridge(
        VOTE_START_PATH,
        {
            "text": message.text,
            "chat_type": chat.chat_type,
            "user_id": user.telegram_id,
            "user_name": user.username,
            "user_full_name": user.full_name,
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        code = bridge_payload.get("code")

        if status == "alert":
            await message.answer(_resolve_vote_text(msg, code, "unexpected_error"))
            return
        if status == "error":
            logging.warning("go vote bridge start returned error status")
        elif status != "ok":
            return

        if status == "ok":
            state = _extract_vote_state(bridge_payload)
            if state is None or not state["media_file_id"]:
                await message.answer(_resolve_vote_text(msg, code, "unexpected_error"))
                return

            build_keyboard = Keyboard(
                amount_photos=str(state["amount_photos"]),
                current_photo_id=str(state["current_photo_id"]),
                current_photo_count=str(state["current_photo_count"]),
                group_id=str(state["group_id"]),
            )
            keyboard = await choose_keyboard(
                state["is_liked_photo"],
                state["current_photo_count"],
                state["amount_photos"],
                build_keyboard,
            )
            caption = _resolve_vote_text(msg, code, "greeting_message_vote")

            if state["media_type"] == "document":
                await bot.send_document(
                    chat_id=chat.telegram_id,
                    caption=caption,
                    document=state["media_file_id"],
                    reply_markup=keyboard,
                )
            else:
                await bot.send_photo(
                    chat_id=chat.telegram_id,
                    caption=caption,
                    photo=state["media_file_id"],
                    reply_markup=keyboard,
                )
            return

    return_text, err, photo_ids = await internal_start(
        chat, user, message.text, like_engine
    )

    if err or not photo_ids:
        await message.answer(return_text)
        return

    user_obj = ObjectFactory.build_user(user.username, user.full_name, user.telegram_id)

    start_data = message.text.replace("_", " ").split()
    group_id = int(start_data[1])
    register_unit = RegisterDB(like_engine.engine)
    await register_unit.register_user(user_obj, group_id)
    photo_file_id, photo_id = await like_engine.select_next_contest_photo(group_id, 0)
    build_keyboard = Keyboard(
        amount_photos=str(len(photo_ids)),
        current_photo_id=photo_id,
        current_photo_count="1",
        group_id=str(group_id),
    )
    is_liked_photo = await like_engine.is_photo_liked(user.telegram_id, photo_id)
    keyboard = await choose_keyboard(
        is_liked_photo,
        1,
        len(photo_ids),
        build_keyboard,
    )
    file_type = await like_engine.select_file_type(int(photo_id))
    if file_type == "photo":
        await bot.send_photo(
            chat_id=chat.telegram_id,
            caption=return_text,
            photo=photo_file_id,
            reply_markup=keyboard,
        )
    elif file_type == "document":
        await bot.send_document(
            chat_id=chat.telegram_id,
            caption=return_text,
            document=photo_file_id,
            reply_markup=keyboard,
        )


async def callback_next(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: LikeDB
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    bridge_payload = await _call_vote_bridge(
        VOTE_NEXT_PATH,
        {
            "user_id": query.from_user.id,
            "group_id": int(cb.group_id),
            "current_photo_id": int(cb.current_photo_id),
            "current_photo_count": int(cb.current_photo_count),
            "amount_photos": int(cb.amount_photos),
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        if status == "noop":
            return
        if status == "ok":
            state = _extract_vote_state(bridge_payload)
            if state is None or not state["media_file_id"]:
                return

            cb.current_photo_count = str(state["current_photo_count"])
            cb.current_photo_id = str(state["current_photo_id"])

            build_keyboard = Keyboard.fromcallback(cb)
            if state["media_type"] == "photo":
                obj = InputMediaPhoto(type="photo", media=state["media_file_id"])
            else:
                obj = InputMediaDocument(type="document", media=state["media_file_id"])

            keyboard = await choose_keyboard(
                state["is_liked_photo"],
                state["current_photo_count"],
                state["amount_photos"],
                build_keyboard,
            )
            await query.message.edit_media(media=obj, reply_markup=keyboard)
            return

    if int(cb.current_photo_count) + 1 > int(cb.amount_photos):
        return

    photo_file_id, photo_id = await like_engine.select_next_contest_photo(
        int(cb.group_id), int(cb.current_photo_id)
    )

    cb.current_photo_count = str(int(cb.current_photo_count) + 1)
    cb.current_photo_id = photo_id

    build_keyboard = Keyboard.fromcallback(cb)
    file_type = await like_engine.select_file_type(int(photo_id))
    if file_type == "photo":
        obj = InputMediaPhoto(type="photo", media=photo_file_id)
    else:
        obj = InputMediaDocument(type="document", media=photo_file_id)
    is_liked_photo = await like_engine.is_photo_liked(query.from_user.id, photo_id)

    keyboard = await choose_keyboard(
        is_liked_photo,
        int(cb.current_photo_count),
        int(cb.amount_photos),
        build_keyboard,
    )
    await query.message.edit_media(media=obj, reply_markup=keyboard)


async def callback_prev(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: LikeDB
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    bridge_payload = await _call_vote_bridge(
        VOTE_PREV_PATH,
        {
            "user_id": query.from_user.id,
            "group_id": int(cb.group_id),
            "current_photo_id": int(cb.current_photo_id),
            "current_photo_count": int(cb.current_photo_count),
            "amount_photos": int(cb.amount_photos),
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        if status == "noop":
            return
        if status == "ok":
            state = _extract_vote_state(bridge_payload)
            if state is None or not state["media_file_id"]:
                return

            cb.current_photo_count = str(state["current_photo_count"])
            cb.current_photo_id = str(state["current_photo_id"])

            build_keyboard = Keyboard.fromcallback(cb)
            if state["media_type"] == "photo":
                obj = InputMediaPhoto(type="photo", media=state["media_file_id"])
            else:
                obj = InputMediaDocument(type="document", media=state["media_file_id"])

            keyboard = await choose_keyboard(
                state["is_liked_photo"],
                state["current_photo_count"],
                state["amount_photos"],
                build_keyboard,
            )
            await query.message.edit_media(media=obj, reply_markup=keyboard)
            return

    if int(cb.current_photo_count) - 1 < 1:
        return

    photo_file_id, photo_id = await like_engine.select_prev_contest_photo(
        int(cb.group_id), int(cb.current_photo_id)
    )

    cb.current_photo_count = str(int(cb.current_photo_count) - 1)
    cb.current_photo_id = photo_id

    build_keyboard = Keyboard.fromcallback(cb)
    file_type = await like_engine.select_file_type(int(photo_id))
    if file_type == "photo":
        obj = InputMediaPhoto(type="photo", media=photo_file_id)
    else:
        obj = InputMediaDocument(type="document", media=photo_file_id)
    is_liked_photo = await like_engine.is_photo_liked(query.from_user.id, int(photo_id))

    keyboard = await choose_keyboard(
        is_liked_photo,
        int(cb.current_photo_count),
        int(cb.amount_photos),
        build_keyboard,
    )
    await query.message.edit_media(media=obj, reply_markup=keyboard)


async def callback_set_like(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: LikeDB, msg: dict
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    bridge_payload = await _call_vote_bridge(
        VOTE_LIKE_PATH,
        {
            "user_id": query.from_user.id,
            "group_id": int(cb.group_id),
            "current_photo_id": int(cb.current_photo_id),
            "current_photo_count": int(cb.current_photo_count),
            "amount_photos": int(cb.amount_photos),
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        code = bridge_payload.get("code")
        if status == "alert":
            await query.answer(
                text=_resolve_vote_text(msg, code, "vote_self"),
                show_alert=True,
            )
            return
        if status == "ok":
            state = _extract_vote_state(bridge_payload)
            if state is None:
                return
            cb.current_photo_count = str(state["current_photo_count"])
            cb.current_photo_id = str(state["current_photo_id"])
            bk = Keyboard.fromcallback(cb)
            keyboard = await choose_keyboard(
                state["is_liked_photo"],
                state["current_photo_count"],
                state["amount_photos"],
                bk,
            )
            await query.message.edit_reply_markup(reply_markup=keyboard)
            return

    vote_result = await like_engine.like_photo(query.from_user.id, int(cb.current_photo_id))
    if (vote_result == -1):
        await query.answer(text=msg["vote"]["vote_self"], show_alert=True)
        return

    bk = Keyboard.fromcallback(cb)
    keyboard = await choose_keyboard(
        1, int(cb.current_photo_count), int(cb.amount_photos), bk
    )
    await query.message.edit_reply_markup(reply_markup=keyboard)


async def callback_vote_self(
    query: CallbackQuery, msg: dict
):
    if not query.message or not query.message.from_user:
        return

    await query.answer(text=msg["vote"]["vote_self"], show_alert=True)


async def callback_set_no_like(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: LikeDB
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    bridge_payload = await _call_vote_bridge(
        VOTE_UNLIKE_PATH,
        {
            "user_id": query.from_user.id,
            "group_id": int(cb.group_id),
            "current_photo_id": int(cb.current_photo_id),
            "current_photo_count": int(cb.current_photo_count),
            "amount_photos": int(cb.amount_photos),
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        if status == "ok":
            state = _extract_vote_state(bridge_payload)
            if state is None:
                return
            cb.current_photo_count = str(state["current_photo_count"])
            cb.current_photo_id = str(state["current_photo_id"])
            bk = Keyboard.fromcallback(cb)
            keyboard = await choose_keyboard(
                state["is_liked_photo"],
                state["current_photo_count"],
                state["amount_photos"],
                bk,
            )
            await query.message.edit_reply_markup(reply_markup=keyboard)
            return
        if status == "noop":
            return

    await like_engine.remove_like_photo(query.from_user.id, int(cb.current_photo_id))

    bk = Keyboard.fromcallback(cb)
    keyboard = await choose_keyboard(
        0, int(cb.current_photo_count), int(cb.amount_photos), bk
    )
    await query.message.edit_reply_markup(reply_markup=keyboard)


async def callback_send_vote(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: LikeDB, msg: dict
):
    if not query.message:
        return
    cb = callback_data

    bridge_payload = await _call_vote_bridge(
        VOTE_SUBMIT_PATH,
        {
            "user_id": query.from_user.id,
            "group_id": int(cb.group_id),
        },
    )
    if bridge_payload is not None:
        status = bridge_payload.get("status")
        code = bridge_payload.get("code")
        if status == "alert":
            await query.answer(
                text=_resolve_vote_text(msg, code, "already_voted"),
                show_alert=True,
            )
            return
        if status == "ok":
            try:
                obj = InputMediaPhoto(type="photo", media=PLACEHOLDER)
                await query.message.edit_media(media=obj, reply_markup=None)
            except TelegramAPIError as e:
                print(e)
            await query.message.edit_caption(
                caption=_resolve_vote_text(msg, code, "thanks_for_vote")
            )
            return
        if status == "noop":
            return

    vote_db = VoteDB(like_engine.engine)

    if (
        await vote_db.is_user_not_allowed_to_vote(int(cb.group_id), query.from_user.id)
        is True
    ):
        await query.answer(text=msg["vote"]["already_voted"], show_alert=True)
        return

    await like_engine.insert_all_likes(query.from_user.id, int(cb.group_id))
    await like_engine.delete_likes_from_tmp_vote(query.from_user.id, int(cb.group_id))
    await vote_db.mark_user_voted(int(cb.group_id), query.from_user.id)
    try:
        obj = InputMediaPhoto(type="photo", media=PLACEHOLDER)
        await query.message.edit_media(media=obj, reply_markup=None)
    except TelegramAPIError as e:
        print(e)
    await query.message.edit_caption(caption=msg["vote"]["thanks_for_vote"])


async def choose_keyboard(
    is_liked_photo: int,
    current_photo_count: int,
    amount_photo: int,
    build_keyboard: Keyboard,
):
    if is_liked_photo == -1:
        if current_photo_count >= int(amount_photo):
            keyboard = build_keyboard.keyboard_end_self
        elif current_photo_count == 1:
            keyboard = build_keyboard.keyboard_start_self
        else:
            keyboard = build_keyboard.keyboard_vote_self
    elif is_liked_photo == 0:
        if current_photo_count >= int(amount_photo):
            keyboard = build_keyboard.keyboard_end
        elif current_photo_count == 1:
            keyboard = build_keyboard.keyboard_start
        else:
            keyboard = build_keyboard.keyboard_vote
    else:
        if current_photo_count >= int(amount_photo):
            keyboard = build_keyboard.keyboard_end_liked
        elif current_photo_count == 1:
            keyboard = build_keyboard.keyboard_start_liked
        else:
            keyboard = build_keyboard.keyboard_vote_liked
    return keyboard
