from db.db_operations import PhotoRegistrationStatus
from services.vote_backend import VoteBackend
from utils.TelegramUserClass import Document, Photo, TelegramChat, TelegramUser


async def internal_register_photo(
    user_object: TelegramUser,
    chat_object: TelegramChat,
    register_backend: VoteBackend,
    contest_material: Photo | Document,
    msg: dict,
) -> str:
    if isinstance(contest_material, Document):
        type_object = "document"
    else:
        type_object = "photo"

    registration_result = await register_backend.register_contest_submission(
        chat_object.telegram_id,
        user_object.telegram_id,
        user_object.username,
        user_object.full_name,
        contest_material.file_id,
        type_object,
    )

    if registration_result == PhotoRegistrationStatus.NEW:
        return msg["register_photo"]["photo_registered"]
    if registration_result == PhotoRegistrationStatus.CHANGED:
        return msg["register_photo"]["photo_changed"]
    return msg["register_photo"]["photo_not_registered"]
