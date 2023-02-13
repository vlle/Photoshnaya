import datetime
from aiogram.methods import SendMessage
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, JOIN_TRANSITION
from db.db_classes import Base
from sqlalchemy import MetaData, create_engine
from db.db_operations import build_group, build_user, register_user, set_register_photo, register_group
from aiogram import F
import time
import redis
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ChatMemberUpdatedFilter
from aiogram.types import Message, Chat, ChatMemberUpdated

logging.basicConfig(level=logging.INFO)
bot = Bot(token="5811948834:AAGl_bFk61wHJXeS2nHLihcAVTAbwMT55JA")

dp = Dispatcher()
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
redis = redis.Redis(connection_pool=pool)

engine = create_engine("sqlite+pysqlite:///photo.db", echo=True)
Base.metadata.create_all(engine)

async def tasks_queue(bot):
    while True:
        try:
            msgs = redis.lpop('queue')
            try:
                st = msgs.decode("utf-8")
                await bot.send_message('415791107', st)
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
    user = build_user(message.from_user.full_name,message.from_user.full_name, message.from_user.id)
    msg = register_user(engine, user, message.chat.id)
    await message.answer(msg)
    

@dp.message(F.caption_entities)
async def example(message: types.Message):#, chat: types.Chat):
    message_contains_hashtag = False
    for i in message.caption_entities:
        if (i.type == 'hashtag'):
            message_contains_hashtag = True
    if (message_contains_hashtag == True):
        set_register_photo(engine, str(message.from_user.id), str(message.chat.id))
        await message.answer("Зарегал фотку!")

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_join(message: types.Message): 
        msg = "Добавили в чат, здоров!"
        group = build_group(message.chat.full_name, str(message.chat.id), "none")
        reg_msg = register_group(engine, group)
        await bot.send_message(message.chat.id, msg)
        await bot.send_message(message.chat.id, reg_msg)


@dp.message((Command(commands=["start"])))
async def cmd_start(message: types.Message):
    now = datetime.datetime.now()
    print(message)
    redis.rpush('queue', str(now))
    await message.answer("Hello!")

async def main():
    txt = '1'
    await asyncio.gather(dp.start_polling(bot), tasks_queue(bot))

if __name__ == "__main__":
    asyncio.run(main())
