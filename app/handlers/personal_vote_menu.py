from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InputMediaDocument, InputMediaPhoto

from db.db_operations import LikeDB, ObjectFactory, RegisterDB, VoteDB
from handlers.internal_logic.vote_start import internal_start
from utils.keyboard import CallbackVote, Keyboard
from utils.TelegramUserClass import TelegramDeserialize

PLACEHOLDER = "AgACAgIAAxkBAAIbk2SlfwGmaPoK776SSq0OYGaZwi6wAAJtyjEbMIUoSXnXybpELj9PAQADAgADeAADLwQ"


# debug function
async def get_file_id(message: types.Message):
    if not message.photo:
        return
    file_id = message.photo[-1].file_id
    await message.answer(file_id)


async def cmd_start(message: types.Message, bot: Bot, like_engine: LikeDB):
    if not message.text or not message.from_user:
        return

    user, chat = TelegramDeserialize.unpack(message)
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
