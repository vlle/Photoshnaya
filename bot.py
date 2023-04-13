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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, ChatMemberUpdatedFilter

from sqlalchemy import create_engine
from db.db_classes import Base
from db.db_operations import build_group, build_theme, build_user, register_user, select_contest_photos_ids, set_register_photo, register_group, register_admin, set_contest_theme, check_admin, get_contest_theme

class CallbackVote(CallbackData, prefix="vote"):
    user: str
    action: str

class Actions():
    next = "=>"
    prev = "<="
    no_like = '🤍'
    like = '❤️"'

class KeyboardButtons():
    def __init__(self, user) -> None:
        self.actions = Actions()
        self.callback_data = CallbackVote(user=user, action="none")
        self.button_next = InlineKeyboardButton(
                text=self.actions.next,
                callback_data=CallbackVote(user=user,
                                              action=self.
                                              actions.next).pack()
                )
        self.button_prev = InlineKeyboardButton(
                text=self.actions.prev,
                callback_data=CallbackVote(user=user,
                                              action=self.
                                              actions.prev
                                              ).pack()
                )
        self.button_back = InlineKeyboardButton(
                text=self.actions.no_like,
                callback_data=CallbackVote(user=user,
                                              action=self.
                                              actions.no_like).pack()
                )


class Keyboard():
    def __init__(self, user: str) -> None:
        self.buttons = KeyboardButtons(user)
        self.keyboard_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_next],
                    [self.buttons.button_prev]
                    ]
                )
        self.keyboard_back = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_back]
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
    pass
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

from aiogram.types import CallbackQuery
@dp.callback_query(CallbackVote.filter(F.action == Actions.next))
async def callback_back(query: CallbackQuery,
                        callback_data: CallbackVote, bot: Bot):
    if not query.message or not query.message.from_user:
        return
    chat_id = query.message.chat.id
    msg_id = query.message.message_id
    user_id = callback_data.user
    build_keyboard = Keyboard(user_id)
    await bot.edit_message_text("Привет.", user_id, msg_id,
                                    parse_mode="html",
                                    reply_markup=build_keyboard.keyboard_vote)
    await query.answer("Возвращаюсь.")

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
        build_keyboard = Keyboard(user_id)

        msg = "Голосуйте за фотографии!"
        await message.answer(
                msg,
                reply_markup=build_keyboard.keyboard_vote
                )

    print(message)
    # builder = InlineKeyboardBuilder()
    # 
    # for index in range(1, 11):
    #     builder.button(text=f"Set {index}", callback_data=f"set:{index}")
    # 
    # builder.adjust(3, 2)
    # 
    # await message.answer("Some text here", reply_markup=builder.as_markup())



async def main():
    logging.basicConfig(level=logging.INFO)
    await asyncio.gather(dp.start_polling(bot), tasks_queue(bot))

if __name__ == "__main__":
    asyncio.run(main())


