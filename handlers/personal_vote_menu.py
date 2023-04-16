from aiogram import types
from aiogram import Bot
from aiogram.filters import callback_data
from aiogram.types import CallbackQuery, InputMediaPhoto
from magic_filter.operations import call
from utils.keyboard import Keyboard, CallbackVote
from sqlalchemy import Engine
from db.db_operations import Like, select_contest_photos_ids, select_next_contest_photo, select_prev_contest_photo, select_file_id

async def cmd_start(message: types.Message, bot: Bot, engine: Engine, like_engine: Like):
    if (not message.text or len(message.text.split(' ')) == 1):
        return
    group_id = message.text.split(' ')[1]
    if (message.chat.type != 'private'):
        return
    try:
        photo_ids = select_contest_photos_ids(engine, int(group_id))
    except:
        await bot.send_message(text="Ошибка в cmd_start, не сгенерировалось голосование", chat_id=message.chat.id)
        return
    if len(photo_ids) == 0:
        return

    amount_photo = 0
    for _ in photo_ids:
        amount_photo += 1

    print(callback_data)
    msg = "Голосуйте за фотографии!"
    user_id = message.from_user.id
    file_id = like_engine.select_next_contest_photo(int(group_id), 0)
    build_keyboard = Keyboard(user=str(user_id), amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count='1', group_id=group_id)
    is_liked_photo = like_engine.is_photo_liked(user_id, file_id[1])
    if (is_liked_photo <= 0):
        await bot.send_photo(chat_id=message.chat.id, caption=msg, photo=file_id[0], reply_markup=build_keyboard.keyboard_start)
    else:
        await bot.send_photo(chat_id=message.chat.id, caption=msg, photo=file_id[0], reply_markup=build_keyboard.keyboard_start_liked)


async def callback_next(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot, like_engine: Like):
    if not query.message or not query.message.from_user:
        return
    print(callback_data)

    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = int(callback_data.current_photo_count) + 1
    if (current_photo_count > int(amount_photo)):
        return
    msg_id = query.message.message_id
    user_id = callback_data.user
    file_id = like_engine.select_next_contest_photo(int(group_id), int(current_photo_id))
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count=str(current_photo_count), group_id=group_id)
    print(file_id)
    obj = InputMediaPhoto(type='photo', media=file_id[0])
    is_liked_photo = like_engine.is_photo_liked(int(user_id), file_id[1])
    if (is_liked_photo <= 0):
        if (current_photo_count == 1):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_start)
        elif (current_photo_count >= int(amount_photo)):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_end)
        else:
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_vote)
    else:
        if (current_photo_count == 1):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_start_liked)
        elif (current_photo_count >= int(amount_photo)):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_end_liked)
        else:
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_vote_liked)

async def callback_prev(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot, like_engine: Like):
    if not query.message or not query.message.from_user:
        return
    print(callback_data)

    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = int(callback_data.current_photo_count) - 1
    if (current_photo_count < 1):
        return

    msg_id = query.message.message_id
    user_id = callback_data.user
    file_id = like_engine.select_prev_contest_photo(int(group_id), int(current_photo_id))
    print(file_id)

    is_liked_photo = like_engine.is_photo_liked(int(user_id), file_id[1])

    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count=str(current_photo_count), group_id=group_id)
    obj = InputMediaPhoto(type='photo', media=file_id[0])
    if (is_liked_photo <= 0):
        if (current_photo_count == 1):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_start)
        elif (current_photo_count >= int(amount_photo)):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_end)
        else:
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_vote)
    else:
        if (current_photo_count == 1):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_start_liked)
        elif (current_photo_count >= int(amount_photo)):
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_end_liked)
        else:
            await bot.edit_message_media(obj, user_id, msg_id,
                                     reply_markup=build_keyboard.keyboard_vote_liked)



async def callback_set_like(query: CallbackQuery,
                            callback_data: CallbackVote, bot: Bot, like_engine: Like):
    if not query.message or not query.message.from_user:
        return
    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = callback_data.current_photo_count 
    msg_id = query.message.message_id
    user_id = callback_data.user

    like_engine.like_photo(int(user_id), int(callback_data.current_photo_id))

    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=current_photo_id, current_photo_count=current_photo_count, group_id=group_id)
    if (int(current_photo_count) >= int(amount_photo)):
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_end_liked)
    elif (int(current_photo_count) <= 1):
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_start_liked)
    else:
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_vote_liked)


async def callback_set_no_like(query: CallbackQuery,
                               callback_data: CallbackVote, bot: Bot, like_engine: Like):
    if not query.message or not query.message.from_user:
        return
    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    user_id = callback_data.user
    current_photo_id = callback_data.current_photo_id
    current_photo_count = callback_data.current_photo_count
    msg_id = query.message.message_id

    like_engine.remove_like_photo(int(user_id), int(callback_data.current_photo_id))

    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=current_photo_id, current_photo_count=current_photo_count, group_id=group_id)
    if (int(current_photo_count) >= int(amount_photo)):
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_end)
    elif (int(current_photo_count) <= 1):
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_start)
    else:
        await bot.edit_message_reply_markup(user_id, msg_id,
                                            reply_markup=build_keyboard.keyboard_vote)


async def send_vote():
    pass
