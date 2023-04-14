import datetime
import configparser
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import redis
import asyncio
import logging

from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import JOIN_TRANSITION
from aiogram.filters.callback_data import CallbackData
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.filters import Command, ChatMemberUpdatedFilter

from sqlalchemy import create_engine
from db.db_classes import Base
from db.db_operations import build_group, build_theme, build_user, register_user, select_contest_photos_ids, set_register_photo, register_group, register_admin, set_contest_theme, check_admin, get_contest_theme, select_next_contest_photo

class CallbackVote(CallbackData, prefix="vote"):
    user: str
    action: str
    current_photo_count: str
    current_photo_id: str
    amount_photos: str
    group_id: str

class Actions():
    next = "➡️"
    prev = "⬅️"
    no_like = '🤍'
    like = '❤️'
    amount = '/'
    count = '-'

class KeyboardButtons():
    def __init__(self, user, group_id, current_photo_id, current_photo_count, amount_photos) -> None:
        self.actions = Actions()
        self.callback_data = CallbackVote(user=user,
                                          action="none",
                                          current_photo_id=current_photo_id,
                                          current_photo_count=current_photo_count,
                                          amount_photos=amount_photos,
                                          group_id=group_id)
        self.button_next = InlineKeyboardButton(
                text=self.actions.next,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.next,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.button_prev = InlineKeyboardButton(
                text=self.actions.prev,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.prev,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.no_like = InlineKeyboardButton(
                text=self.actions.no_like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.no_like,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.like = InlineKeyboardButton(
                text=self.actions.like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.like,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id='').pack()
                )
        self.amount = InlineKeyboardButton(
                text=current_photo_count+self.actions.amount+amount_photos,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.count,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )


class Keyboard():
    def __init__(self, user: str, current_photo_id: str, current_photo_count: str, amount_photos: str, group_id: str) -> None:
        self.buttons = KeyboardButtons(user, group_id, current_photo_id, current_photo_count, amount_photos)
        self.keyboard_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
                     self.buttons.amount,
                     self.buttons.button_next],
                    [self.buttons.no_like]
                    ]
                )
        self.keyboard_liked_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
                     self.buttons.amount,
                     self.buttons.button_next],
                    [self.buttons.like]
                    ]
                )

config = configparser.ConfigParser()
config.read('config.txt')
token = config['DEFAULT']['token']
redis_port = config['DEFAULT']['redis_port']
redis_host = config['DEFAULT']['redis_host']
redis_db = config['DEFAULT']['redis_db']
bot = Bot(token=token)
dp = Dispatcher()
pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)
redis = redis.Redis(connection_pool=pool)

engine = create_engine("sqlite+pysqlite:///photo.db", echo=True)
Base.metadata.create_all(engine)


@dp.message((Command(commands=["send"])))
async def writer(m: types.Message):
    for i in range(0, 10):
        push = m.text.split()
        redis.rpush("queue", push[-1])


@dp.message((Command(commands=["register"])))
async def register(message: types.Message):
    msg = "None yet"
    if (message.from_user and message.from_user.full_name and
        message.from_user.id and message.chat and message.chat.id):
        user = build_user(message.from_user.full_name,
                          message.from_user.full_name,
                          str(message.from_user.id))
        msg = register_user(engine, user, str(message.chat.id))
        await message.answer(msg)


@dp.message(F.caption_entities)
@dp.edited_message(F.caption_entities)
async def register_photo(message: types.Message):
    if not message.caption:
        return
    theme = get_contest_theme(engine, str(message.chat.id))
    message_search = message.caption.split()
    message_contains_contest = False
    for word in message_search:
        if (word == theme):
            message_contains_contest = True
            break
    if (message_contains_contest is True):
        if (message.from_user and message.from_user.id
            and message.chat and message.chat.id):
            user = build_user(str(message.from_user.username),
                              message.from_user.full_name,
                              str(message.from_user.id))
            group = build_group(message.chat.full_name,
                                str(message.chat.id),
                                "none")
            register_user(engine, user, str(message.chat.id))
            if message.photo:
                file_id = message.photo[-1].file_id
                set_register_photo(engine, str(message.from_user.id),
                                   str(message.chat.id), file_get_id=file_id, user_p=user, group_p=group)
                await message.answer(f"{file_id}")
                await bot.send_photo(message.chat.id,file_id)
            else:
                set_register_photo(engine, str(message.from_user.id),
                                   str(message.chat.id), file_get_id='-1', user_p=user, group_p=group)
            await message.answer(f"Зарегал фотку! Тема: {theme} ")


@dp.my_chat_member(ChatMemberUpdatedFilter(
    member_status_changed=JOIN_TRANSITION))
async def on_user_join(message: types.Message):
    msg = "Добавили в чат, здоров!"
    group = build_group(message.chat.full_name, str(message.chat.id), "none")
    reg_msg = register_group(engine, group)
    if (message.from_user and message.from_user.username):
        adm_user = build_user(message.from_user.username,
                              message.from_user.full_name,
                              str(message.from_user.id))
        register_admin(engine, adm_user, str(message.chat.id))
        msg = f"Добавил в качестве админа {message.from_user.username}"
    if (message.chat and message.chat.id):
        await bot.send_message(message.chat.id, msg)
        await bot.send_message(message.chat.id, reg_msg)


@dp.message((Command(commands=["set_theme"])))
async def set_theme(message: types.Message):
    if not message.text or not message.from_user:
        return
    user_theme = message.text.split()
    user_id = str(message.from_user.id)
    group_id = str(message.chat.id)
    admin_right = check_admin(engine, user_id, group_id)
    if admin_right is False:
        msg = "Нельзя, ты не админ."
        await bot.send_message(message.chat.id, msg)
        return
    theme = build_theme(user_theme)
    if (len(user_theme) == 1):
        msg = 'Забыл название темы, админ\nПример: /set_theme #пляжи'
        await bot.send_message(message.chat.id, msg)
        return msg

    time = 604800
    msg = set_contest_theme(engine, user_id, group_id, theme, time)
    # redis.rpush(int(message.chat.id), time)
    await bot.send_message(message.chat.id, msg)

@dp.message((Command(commands=["finish_contest"])))
async def set_theme(message: types.Message):
    if not message.text or not message.from_user:
        return
    user_theme = message.text.split()
    user_id = str(message.from_user.id)
    group_id = str(message.chat.id)
    admin_right = check_admin(engine, user_id, group_id)
    if admin_right is False:
        msg = "Нельзя, ты не админ."
        await bot.send_message(message.chat.id, msg)
        return
    photo_ids = select_contest_photos_ids(engine, group_id)
    for i in photo_ids:
        await bot.send_photo(message.chat.id, i)

@dp.message((Command(commands=["get_theme"])))
async def get_theme(message: types.Message):
    if not message.chat or not message.chat.id:
        return

    chat_id = str(message.chat.id)
    theme = get_contest_theme(engine, chat_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


#set admin -- update and etc and tests

@dp.message((Command(commands=["start"])))
async def cmd_start(message: types.Message):
    if (not message.text or len(message.text.split(' ')) == 1):
        return
    group_id = message.text.split(' ')[1]
    print(f"group = {group_id}")
    if (message.chat.type != 'private'):
        return
    photo_ids = select_contest_photos_ids(engine, group_id)
    amount_photo = 0
    for _ in photo_ids:
        amount_photo += 1

    msg = "Голосуйте за фотографии!"
    user_id = str(message.from_user.id)
    file_id = select_next_contest_photo(engine, group_id, 0)
    print("file file")
    print("file file")
    print("file file")
    print(file_id)
    print("file file")
    print("file file")
    print("file file")
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count='0', group_id=group_id)

    await bot.send_photo(chat_id=message.chat.id, caption=msg, photo=file_id[0], reply_markup=build_keyboard.keyboard_vote)

def get_next_photo(file_vote: str, current_photo: int):
    return 


from aiogram.types import CallbackQuery
@dp.callback_query(CallbackVote.filter(F.action == Actions.next))
async def callback_back(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    print(callback_data)

    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    if (current_photo_id == amount_photo):
        return
    msg_id = query.message.message_id
    user_id = callback_data.user
    file_id = select_next_contest_photo(engine, group_id, int(current_photo_id))
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id=file_id[1], current_photo_count='0', group_id=group_id)
    #obj = InputMediaPhoto(type='photo', media='AgACAgIAAx0CbZceowACg2tkOCCQpjGRr7EodlW--7-hh47TUAACwM8xG076wUni_vosbbwAAfkBAAMCAAN5AAMvBA')
    print(file_id)
    obj = InputMediaPhoto(type='photo', media=file_id[0])
    await bot.edit_message_media(obj, user_id, msg_id,
                                 reply_markup=build_keyboard.keyboard_vote)
    await query.answer("Возвращаюсь.")

@dp.callback_query(CallbackVote.filter(F.action == Actions.no_like))
async def callback_set_like(query: CallbackQuery,
                            callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    group_id = callback_data.group_id
    amount_photo = callback_data.amount_photos
    current_photo_id = callback_data.current_photo_id
    current_photo_count = callback_data.current_photo_count
    #if (current_photo_id == amount_photo):
    #    return
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo_id='0', current_photo_count='0', group_id=group_id)
    msg_id = query.message.message_id
    user_id = callback_data.user
    await bot.edit_message_reply_markup(user_id, msg_id,
                                        reply_markup=build_keyboard.keyboard_liked_vote)

@dp.callback_query(CallbackVote.filter(F.action == Actions.like))
async def callback_set_no_like(query: CallbackQuery,
                               callback_data: CallbackVote, bot: Bot):
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



async def main():
    logging.basicConfig(level=logging.INFO)
    await asyncio.gather(dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())


