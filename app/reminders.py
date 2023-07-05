import asyncio

from aiogram import Bot
from redis import asyncio as aioredis

REMINDERS_CHANNEL = "reminders"


async def add_reminder(time: int | str, group_id: str) -> None:
    if isinstance(time, int):
        time = str(time)

    r = aioredis.Redis(port=6379, db=0)
    await r.zadd(REMINDERS_CHANNEL, {group_id: time})


async def send_reminders(bot: Bot, message: str) -> None:
    r = aioredis.Redis(port=6379, db=0)
    while True:
        await asyncio.sleep(60)
        current_time_epoch, _ = await r.time()
        current_time = int(current_time_epoch)
        reminders = await r.zrangebyscore(REMINDERS_CHANNEL, 0, current_time)
        for reminder in reminders:
            await bot.send_message(reminder.decode("utf-8"), message)
            await r.zrem(REMINDERS_CHANNEL, reminder)
