import datetime
import configparser
from aiogram.methods import SendMessage
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, JOIN_TRANSITION, IS_ADMIN
from db.db_classes import Base
from sqlalchemy import MetaData, create_engine
from db.db_operations import build_group, build_user, register_user, set_register_photo, register_group, register_admin, get_admins, set_contest_theme, check_admin, get_contest_theme
from aiogram import F
import time
import redis
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ChatMemberUpdatedFilter
from aiogram.types import Message, Chat, ChatMemberUpdated

logging.basicConfig(level=logging.INFO)
config = configparser.ConfigParser()
config.read('config.txt')
token = config['DEFAULT']['token']
print(token)
bot = Bot(token=token)

dp = Dispatcher()
# pool = redis.ConnectionPool(host='localhost', port=6309, db=0)
# redis = redis.Redis(connection_pool=pool)

engine = create_engine("sqlite+pysqlite:///photo.db", echo=True)
Base.metadata.create_all(engine)

# async def tasks_queue(bot):
#     while True:
#         try:
#             msgs = redis.lpop('queue')
#             try:
#                 st = msgs.decode("utf-8")
#                 await bot.send_message('415791107', st)
#                 if (st[-1] != 'd'):
#                     try:
#                         await asyncio.sleep(int(st[-1]))
#                     except ValueError:
#                         pass
#             except AttributeError:
#                 await asyncio.sleep(1)
#         except TimeoutError:
#             await m.answer("Рассылка закончена")
#             break


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
async def register_photo(message: types.Message):
    theme = get_contest_theme(engine, message.chat.id)
    message_search = message.caption.split()
    message_contains_contest = False
    for word in message_search:
        if (word == theme):
            message_contains_contest = True
            break
    if (message_contains_contest is True):
        if (message.from_user and message.from_user.id
                and message.chat and message.chat.id):
            user = build_user(message.from_user.username,
                              message.from_user.full_name,
                              message.from_user.id)
            group = build_group(message.chat.full_name,
                                str(message.chat.id),
                                "none")
            register_user(engine, user, str(message.chat.id))
            set_register_photo(engine, str(message.from_user.id),
                               str(message.chat.id), user, group)
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
        await bot.send_message(message.chat.id, msg)
    if (message.chat and message.chat.id):
        await bot.send_message(message.chat.id, msg)
        await bot.send_message(message.chat.id, reg_msg)


@dp.message((Command(commands=["set_theme"])))
async def set_theme(message: types.Message):
    # maybe cooldown if no available
    user_id = str(message.from_user.id)
    group_id = str(message.chat.id)
    user_theme = message.text.split()
    if (len(user_theme) == 1):
        msg = 'Забыл название темы, админ\nПример: /set_theme #пляжи'
        await bot.send_message(message.chat.id, msg)
        return
    if (user_theme[1][0] != '#'):
        theme = '#' + user_theme[1]
    else:
        theme = user_theme[1]
    admin_right = check_admin(engine, user_id, group_id)
    if admin_right is True:
        msg = set_contest_theme(engine, user_id, group_id, theme)
        await bot.send_message(message.chat.id, msg)
    else:
        msg = "Нельзя, ты не админ."
        await bot.send_message(message.chat.id, msg)


@dp.message((Command(commands=["get_theme"])))
async def get_theme(message: types.Message):
    theme = get_contest_theme(engine, message.chat.id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


#set admin -- update and etc and tests


@dp.message((Command(commands=["start"])))
async def cmd_start(message: types.Message):
    now = datetime.datetime.now()
    redis.rpush('queue', str(now))
    await message.answer("Hello!")

async def main():
    await asyncio.gather(dp.start_polling(bot))#, tasks_queue(bot))

if __name__ == "__main__":
    asyncio.run(main())
