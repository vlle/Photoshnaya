from utils.TelegramUserClass import TelegramChat, TelegramUser, Photo, Document
from db.db_operations import build_user, build_group, register_user, set_register_photo
from sqlalchemy import Engine


def _register_photo(user_object: TelegramUser, chat_object: TelegramChat, engine: Engine, contest_material: Photo | Document) -> str:
    user = build_user(user_object.username,
                      user_object.full_name,
                      user_object.telegram_id)
    group = build_group(chat_object.full_name,
                        chat_object.telegram_id,
                        "none")
    ret = register_user(engine, user, chat_object.telegram_id)
    if isinstance(contest_material, Photo):
        set_register_photo(engine,
                           user_object.telegram_id,
                           chat_object.telegram_id, 
                           file_get_id=contest_material.file_id, user_p=user, group_p=group)
    else:
        set_register_photo(engine,
                           user_object.telegram_id,
                           chat_object.telegram_id,
                           file_get_id='-1',
                           user_p=user,
                           group_p=group)
    return "Зарегистрировал фото."
