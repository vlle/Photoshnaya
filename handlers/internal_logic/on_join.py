from db.db_operations import ObjectFactory, RegisterDB
from utils.TelegramUserClass import TelegramChat, TelegramUser


def i_on_user_join(register_unit: RegisterDB, chat: TelegramChat, user: TelegramUser) -> tuple:

    group = ObjectFactory.build_group(chat.full_name, chat.telegram_id)
    reg_msg, is_registered = register_unit.register_group(group)
    if not is_registered:
        return reg_msg, None

    adm_user = ObjectFactory.build_user(user.username,
                                        user.full_name,
                                        user.telegram_id)
    register_unit.register_admin(adm_user, chat.telegram_id)
    msg = f"Добавил в качестве админа {user.username}"

    return msg, reg_msg
