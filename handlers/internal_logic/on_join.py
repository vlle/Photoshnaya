from db.db_operations import ObjectFactory, Register, set_contest_theme, check_admin, build_theme, build_theme, get_contest_theme
from utils.TelegramUserClass import TelegramChat, TelegramUser

def _on_user_join(obj_factory: ObjectFactory, register_unit: Register, chat: TelegramChat, user: TelegramUser) -> tuple:

    group = obj_factory.build_group(chat.full_name, chat.telegram_id, "none")
    reg_msg, is_registered = register_unit.register_group(group)
    if (is_registered == False):
        return reg_msg, None

    adm_user = obj_factory.build_user(user.username,
                          user.full_name,
                          user.telegram_id)
    register_unit.register_admin(adm_user, chat.telegram_id)
    msg = f"Добавил в качестве админа {user.username}"

    return msg, reg_msg




