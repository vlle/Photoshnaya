from db.db_operations import ObjectFactory, AdminDB
from utils.TelegramUserClass import TelegramChat


async def i_set_theme(user_theme: list[str],
                admin_unit: AdminDB, chat: TelegramChat):
    theme = ObjectFactory.build_theme(user_theme)
    if (len(user_theme) == 1):
        msg = 'Забыл название темы, админ\nПример: /set_theme #пляжи'
    else:
        time = 604800
        msg = await admin_unit.set_contest_theme(chat.telegram_id,
                                           theme, time) + " = новая тема"
    return msg
