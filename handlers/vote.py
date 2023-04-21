from aiogram import types
from aiogram import Bot
from db.db_operations import AdminDB
from utils.TelegramUserClass import TelegramDeserialize


async def finish_contest(message: types.Message,
                         bot: Bot, admin_unit: AdminDB):
    user, chat = TelegramDeserialize.unpack(message)
    if not message.text or not message.from_user:
        return
    admin_right = admin_unit.check_admin(user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return
    # photo_ids = select_contest_photos_ids(engine, group_id)
    # for i in photo_ids:
    #     await bot.send_photo(message.chat.id, i)
