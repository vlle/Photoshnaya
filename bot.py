import datetime
import time
import redis
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="5811948834:AAGl_bFk61wHJXeS2nHLihcAVTAbwMT55JA")
# Диспетчер
dp = Dispatcher()
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
redis = redis.Redis(connection_pool=pool)

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
        print("shit")


# @dp.message((Command(commands=["listen"])))
# async def listener(m: types.Message, batch_size: int = 5, polling_timeout=10):
#     while True:
#         try:
#             msgs = redis.lpop('queue')
#             try:
#                 await bot.send_message('1919118841', msgs.decode("utf-8"))
#             except TelegramForbiddenError:
#                 pass
#         except TimeoutError:
#             await m.answer("Рассылка закончена")
#             break


@dp.message((Command(commands=["start"])))
async def cmd_start(message: types.Message):
    now = datetime.datetime.now()
    redis.rpush('queue', str(now))
    await message.answer("Hello!")

# Запуск процесса поллинга новых апдейтов
async def main():
    await asyncio.gather(dp.start_polling(bot), tasks_queue(bot))

if __name__ == "__main__":
    asyncio.run(main())


