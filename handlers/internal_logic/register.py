from utils.TelegramUserClass import TelegramChat, TelegramUser, Photo, Document
from db.db_operations import ObjectFactory, RegisterDB


def internal_register_photo(user_object: TelegramUser,
                            chat_object: TelegramChat,
                            register: RegisterDB,
                            contest_material: Photo | Document,
                            msg: dict) -> str:
    if isinstance(contest_material, Document):
        type_object = 'document'
    else:
        type_object = 'photo'

    user = ObjectFactory.build_user(user_object.username,
                                    user_object.full_name,
                                    user_object.telegram_id)
    group = ObjectFactory.build_group(chat_object.full_name,
                                      chat_object.telegram_id)
    register.register_user(user, chat_object.telegram_id)
    if register.register_photo_for_contest(
            user_object.telegram_id,
            chat_object.telegram_id,
            file_get_id=contest_material.file_id,
            user_p=user, group_p=group, type=type_object) is True:
        return msg["register_photo"]["photo_registered"]
    else:
        return msg["register_photo"]["photo_not_registered"]
