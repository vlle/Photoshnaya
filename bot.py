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
from db.db_operations import build_group, build_theme, build_user, register_user, select_contest_photos_ids, set_register_photo, register_group, register_admin, set_contest_theme, check_admin, get_contest_theme

class CallbackVote(CallbackData, prefix="vote"):
    user: str
    action: str
    current_photo: str
    amount_photos: str
    file_vote: str

class Actions():
    next = "=>"
    prev = "<="
    no_like = '🤍'
    like = '❤️'

class KeyboardButtons():
    def __init__(self, user, file_vote, current_photo, amount_photos) -> None:
        self.actions = Actions()
        self.callback_data = CallbackVote(user=user,
                                          action="none",
                                          current_photo=current_photo,
                                          amount_photos=amount_photos,
                                          file_vote=file_vote)
        self.button_next = InlineKeyboardButton(
                text=self.actions.next,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.next,
                                          current_photo=current_photo,
                                          amount_photos=amount_photos,
                                           file_vote=file_vote).pack()
                )
        self.button_prev = InlineKeyboardButton(
                text=self.actions.prev,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.prev,
                                          current_photo=current_photo,
                                          amount_photos=amount_photos,
                                           file_vote=file_vote).pack()
                )
        self.no_like = InlineKeyboardButton(
                text=self.actions.no_like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.no_like,
                                          current_photo=current_photo,
                                          amount_photos=amount_photos,
                                           file_vote=file_vote).pack()
                )
        self.like = InlineKeyboardButton(
                text=self.actions.like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.like,
                                          current_photo='1',
                                          amount_photos=amount_photos,
                                           file_vote='').pack()
                )


class Keyboard():
    def __init__(self, user: str, current_photo: str, amount_photos: str, file_vote: str) -> None:
        self.buttons = KeyboardButtons(user, current_photo, amount_photos, file_vote)
        self.keyboard_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
                     self.buttons.button_next],
                    [self.buttons.no_like]
                    ]
                )
        self.keyboard_liked_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
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

async def tasks_queue(bot):
    # chat = await bot.get_chat()
    return
    while True:
        try:
            msgs = redis.lpop(chat)
            try:
                st = msgs.decode("utf-8")
                await bot.send_message(chat, st + '\n Тема закончилась')
                if (st[-1] != 'd'):
                    try:
                        await asyncio.sleep(int(st[-1]))
                    except ValueError:
                        pass
            except AttributeError:
                await asyncio.sleep(1)
        except TimeoutError:
            await m.answer("Рассылка закончена")
            break


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
    photo_ids = select_contest_photos_ids(engine, group_id)
    for i in photo_ids:
        await bot.send_photo(message.chat.id, i)


    if (message.chat.type == 'private'):
        user_id = str(message.from_user.id)
        photo_ids = select_contest_photos_ids(engine, group_id)
        file_vote = ''
        amount_photo = 0
        current_photo = 1
        for photo_id in photo_ids:
            file_vote += amount_photo+photo_id+','
            amount_photo += 1
        build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo='1', file_vote=file_vote)

        msg = "Голосуйте за фотографии!"
        file_id = 'https://picsum.photos/200'
        await bot.send_photo(chat_id=message.chat.id, caption=msg, photo=file_id, reply_markup=build_keyboard.keyboard_vote)
    print(message)

def get_next_photo(file_vote: str, current_photo: str):
    list_words = file_vote.split(',')
    print(list_words)
    for let in file_vote:
        pass


from aiogram.types import CallbackQuery
@dp.callback_query(CallbackVote.filter(F.action == Actions.next))
async def callback_back(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    file_vote = callback_data.file_vote
    amount_photo = callback_data.amount_photos
    current_photo = callback_data.current_photo
    if (current_photo == amount_photo):
        return
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo='1', file_vote=file_vote)
    file_id = 'https://picsum.photos/200'
    #obj = InputMediaPhoto(type='photo', media='AgACAgIAAx0CbZceowACg2tkOCCQpjGRr7EodlW--7-hh47TUAACwM8xG076wUni_vosbbwAAfkBAAMCAAN5AAMvBA')
    obj = InputMediaPhoto(type='photo', media=file_id)
    file_id = get_next_photo(file_vote, current_photo)
    await bot.edit_message_media(obj, user_id, msg_id,
                                reply_markup=build_keyboard.keyboard_vote)
    await query.answer("Возвращаюсь.")

@dp.callback_query(CallbackVote.filter(F.action == Actions.no_like))
async def callback_set_like(query: CallbackQuery,
                            callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    file_vote = callback_data.file_vote
    amount_photo = callback_data.amount_photos
    current_photo = callback_data.current_photo
    #if (current_photo == amount_photo):
    #    return
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo='1', file_vote=file_vote)
    msg_id = query.message.message_id
    user_id = callback_data.user
    await bot.edit_message_reply_markup(user_id, msg_id,
                                        reply_markup=build_keyboard.keyboard_liked_vote)

@dp.callback_query(CallbackVote.filter(F.action == Actions.like))
async def callback_set_no_like(query: CallbackQuery,
                               callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    file_vote = callback_data.file_vote
    amount_photo = callback_data.amount_photos
    current_photo = callback_data.current_photo
    #if (current_photo == amount_photo):
    #    return
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user=user_id, amount_photos=str(amount_photo), current_photo='1', file_vote=file_vote)
    msg_id = query.message.message_id
    user_id = callback_data.user
    await bot.edit_message_reply_markup(user_id, msg_id,
                                        reply_markup=build_keyboard.keyboard_vote)



async def main():
    logging.basicConfig(level=logging.INFO)
    await asyncio.gather(dp.start_polling(bot), tasks_queue(bot))

if __name__ == "__main__":
    asyncio.run(main())


