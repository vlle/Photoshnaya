from sqlalchemy.exc import IntegrityError
from db.db_operations import ObjectFactory, RegisterDB
from utils.TelegramUserClass import TelegramUser

async def i_del_admin(user_object: TelegramUser, register: RegisterDB,
                      msg: dict):
    user = ObjectFactory.build_user(user_object.username,
                                    user_object.full_name,
                                    user_object.telegram_id)
    try:
        text = msg["del_admin"]["del_adm"]
        await register.unregister_admin(user_object.telegram_id, user_object.chat_id)
    except IntegrityError:
        text = msg["add_admin"]["err"]
    return text
