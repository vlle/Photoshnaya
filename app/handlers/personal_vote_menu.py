from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InputMediaDocument, InputMediaPhoto

from db.db_operations import ObjectFactory, RegisterDB
from handlers.internal_logic.vote_start import internal_start
from services.vote_backend import VoteBackend, VoteBackendBusinessError
from utils.keyboard import CallbackVote, Keyboard
from utils.TelegramUserClass import TelegramDeserialize

PLACEHOLDER = "AgACAgIAAxkBAAIbk2SlfwGmaPoK776SSq0OYGaZwi6wAAJtyjEbMIUoSXnXybpELj9PAQADAgADeAADLwQ"


# debug function
async def get_file_id(message: types.Message):
    if not message.photo:
        return
    file_id = message.photo[-1].file_id
    await message.answer(file_id)


async def cmd_start(message: types.Message, bot: Bot, like_engine: VoteBackend):
    if not message.text or not message.from_user:
        return

    user, chat = TelegramDeserialize.unpack(message)
    return_text, err, vote_session = await internal_start(
        chat, user, message.text, like_engine
    )

    if err or not vote_session:
        await message.answer(return_text)
        return

    user_obj = ObjectFactory.build_user(user.username, user.full_name, user.telegram_id)

    start_data = message.text.replace("_", " ").split()
    group_id = int(start_data[1])
    register_unit = RegisterDB(like_engine.engine)
    await register_unit.register_user(user_obj, group_id)
    build_keyboard = Keyboard(
        amount_photos=str(vote_session.total_photos),
        current_photo_id=str(vote_session.photo_id),
        current_photo_count=str(vote_session.current_index),
        group_id=str(group_id),
    )
    keyboard = await choose_keyboard(
        vote_session.liked_state,
        vote_session.current_index,
        vote_session.total_photos,
        build_keyboard,
    )
    if vote_session.file_type == "photo":
        await bot.send_photo(
            chat_id=chat.telegram_id,
            caption=return_text,
            photo=vote_session.file_id,
            reply_markup=keyboard,
        )
    elif vote_session.file_type == "document":
        await bot.send_document(
            chat_id=chat.telegram_id,
            caption=return_text,
            document=vote_session.file_id,
            reply_markup=keyboard,
        )


async def callback_next(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: VoteBackend
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return
    if int(cb.current_photo_count) + 1 > int(cb.amount_photos):
        return

    vote_state = await like_engine.get_next_vote_photo(
        int(cb.group_id), query.from_user.id, int(cb.current_photo_id)
    )

    cb.current_photo_count = str(vote_state.current_index)
    cb.current_photo_id = str(vote_state.photo_id)

    build_keyboard = Keyboard.fromcallback(cb)
    if vote_state.file_type == "photo":
        obj = InputMediaPhoto(type="photo", media=vote_state.file_id)
    else:
        obj = InputMediaDocument(type="document", media=vote_state.file_id)

    keyboard = await choose_keyboard(
        vote_state.liked_state,
        vote_state.current_index,
        vote_state.total_photos,
        build_keyboard,
    )
    await query.message.edit_media(media=obj, reply_markup=keyboard)


async def callback_prev(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: VoteBackend
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return
    if int(cb.current_photo_count) - 1 < 1:
        return

    vote_state = await like_engine.get_prev_vote_photo(
        int(cb.group_id), query.from_user.id, int(cb.current_photo_id)
    )

    cb.current_photo_count = str(vote_state.current_index)
    cb.current_photo_id = str(vote_state.photo_id)

    build_keyboard = Keyboard.fromcallback(cb)
    if vote_state.file_type == "photo":
        obj = InputMediaPhoto(type="photo", media=vote_state.file_id)
    else:
        obj = InputMediaDocument(type="document", media=vote_state.file_id)

    keyboard = await choose_keyboard(
        vote_state.liked_state,
        vote_state.current_index,
        vote_state.total_photos,
        build_keyboard,
    )
    await query.message.edit_media(media=obj, reply_markup=keyboard)


async def callback_set_like(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: VoteBackend, msg: dict
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    try:
        vote_result = await like_engine.set_like(
            int(cb.group_id), query.from_user.id, int(cb.current_photo_id)
        )
    except VoteBackendBusinessError as err:
        if err.code != "self_like":
            raise
        vote_result = -1

    if vote_result == -1:
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
    query: CallbackQuery, callback_data: CallbackVote, like_engine: VoteBackend
):
    cb = callback_data
    if not query.message or not query.message.from_user:
        return

    await like_engine.unset_like(
        int(cb.group_id), query.from_user.id, int(cb.current_photo_id)
    )

    bk = Keyboard.fromcallback(cb)
    keyboard = await choose_keyboard(
        0, int(cb.current_photo_count), int(cb.amount_photos), bk
    )
    await query.message.edit_reply_markup(reply_markup=keyboard)


async def callback_send_vote(
    query: CallbackQuery, callback_data: CallbackVote, like_engine: VoteBackend, msg: dict
):
    if not query.message:
        return
    cb = callback_data

    try:
        await like_engine.submit_vote(int(cb.group_id), query.from_user.id)
    except VoteBackendBusinessError as err:
        if err.code != "already_voted":
            raise
        await query.answer(text=msg["vote"]["already_voted"], show_alert=True)
        return

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
