from aiogram import types
from aiogram import Bot
from sqlalchemy import Engine
from db.db_operations import select_contest_photos_ids, check_admin

async def finish_contest(message: types.Message, bot: Bot, engine: Engine):
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
