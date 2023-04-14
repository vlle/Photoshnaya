from aiogram import types
from aiogram import Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from utils.keyboard import Keyboard, CallbackVote
from sqlalchemy import Engine
from db.db_operations import select_contest_photos_ids, select_next_contest_photo, select_prev_contest_photo

async def cmd_start(message: types.Message, bot: Bot, engine: Engine):
    if (not message.text or len(message.text.split(' ')) == 1):
        return
    group_id = message.text.split(' ')[1]
    if (message.chat.type != 'private'):
        return
    photo_ids = select_contest_photos_ids(engine, group_id)
    amount_photo = 0
    for _ in photo_ids:
        amount_photo += 1

    msg = "Голосуйте за фотографии!"
    user_id = str(message.from_user.id)
    file_id = select_next_contest_photo(engine, group_id, 0)
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count='0', group_id=group_id)

    await bot.send_photo(chat_id=message.chat.id, caption=msg, photo=file_id[0], reply_markup=build_keyboard.keyboard_vote)


async def callback_next(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot, engine: Engine):
    if not query.message or not query.message.from_user:
        return
    print(callback_data)

    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = int(callback_data.current_photo_count)
    if (current_photo_count >= int(amount_photo)):
        return
    msg_id = query.message.message_id
    user_id = callback_data.user
    file_id = select_next_contest_photo(engine, group_id, int(current_photo_id))
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count=str(current_photo_count+1), group_id=group_id)
    print(file_id)
    obj = InputMediaPhoto(type='photo', media=file_id[0])
    await bot.edit_message_media(obj, user_id, msg_id,
                                 reply_markup=build_keyboard.keyboard_vote)

async def callback_prev(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot, engine: Engine):
    if not query.message or not query.message.from_user:
        return
    print(callback_data)

    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = int(callback_data.current_photo_count)
    if (current_photo_count <= 0):
        return
    msg_id = query.message.message_id
    user_id = callback_data.user
    file_id = select_prev_contest_photo(engine, group_id, int(current_photo_id))
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count=str(current_photo_count-1), group_id=group_id)
    print(file_id)
    obj = InputMediaPhoto(type='photo', media=file_id[0])
    await bot.edit_message_media(obj, user_id, msg_id,
                                 reply_markup=build_keyboard.keyboard_vote)
    #await query.answer("Возвращаюсь.")

async def callback_set_like(query: CallbackQuery,
                            callback_data: CallbackVote, bot: Bot, engine: Engine):
    if not query.message or not query.message.from_user:
        return
    # WIP
    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = callback_data.current_photo_count
    #if (current_photo_id == amount_photo):
    #    return

    #WIP 

    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id='0', current_photo_count='0', group_id=group_id)
    msg_id = query.message.message_id
    user_id = callback_data.user
    await bot.edit_message_reply_markup(user_id, msg_id,
                                        reply_markup=build_keyboard.keyboard_liked_vote)

async def callback_set_no_like(query: CallbackQuery,
                               callback_data: CallbackVote, bot: Bot, engine: Engine):
    if not query.message or not query.message.from_user:
        return
    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id='0', current_photo_count='0', group_id=group_id)
    msg_id = query.message.message_id
    user_id = callback_data.user
    await bot.edit_message_reply_markup(user_id, msg_id,
                                        reply_markup=build_keyboard.keyboard_vote)
