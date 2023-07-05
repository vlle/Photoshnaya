from sqlalchemy.exc import IntegrityError

from db.db_operations import ObjectFactory, RegisterDB
from utils.TelegramUserClass import TelegramUser


async def i_add_admin(user_object: TelegramUser, register: RegisterDB, msg: dict):
    user = ObjectFactory.build_user(
        user_object.username, user_object.full_name, user_object.telegram_id
    )
    text = msg["add_admin"]["add_adm"]
    try:
        text = await register.register_admin(user, user_object.chat_id)
    except IntegrityError:
        text = msg["add_admin"]["err"]
    return text
