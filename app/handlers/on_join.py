from aiogram import Bot, types
from db.db_operations import RegisterDB
from handlers.internal_logic.on_join import i_on_user_join
from utils.TelegramUserClass import TelegramDeserialize


async def on_user_join(message: types.Message, bot: Bot, register_unit: RegisterDB):
    user, chat = TelegramDeserialize.unpack(message, message_id_not_exists=True)

    msg, reg_msg = await i_on_user_join(
        register_unit=register_unit, user=user, chat=chat
    )

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
