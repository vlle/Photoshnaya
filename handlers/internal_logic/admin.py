from db.db_operations import ObjectFactory, set_contest_theme
from utils.TelegramUserClass import TelegramChat, TelegramUser

def i_set_theme(user_theme: list[str], engine, user: TelegramUser, chat: TelegramChat):
    obj_factory = ObjectFactory()
    theme = obj_factory.build_theme(user_theme)
    if (len(user_theme) == 1):
        msg = 'Забыл название темы, админ\nПример: /set_theme #пляжи'
    else:
        time = 604800
        msg = set_contest_theme(engine, user.telegram_id, chat.telegram_id, theme, time) + " = новая тема"
    return msg
