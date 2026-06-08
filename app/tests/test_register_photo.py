from datetime import datetime, timedelta, timezone

from db.db_operations import PhotoRegistrationStatus
from handlers.internal_logic.register import internal_register_photo
from handlers.user_action import is_stale_message
from utils.TelegramUserClass import Document, Photo, TelegramChat, TelegramUser


class FakeRegistrationBackend:
    def __init__(self, status: PhotoRegistrationStatus):
        self.status = status

    async def register_contest_submission(
        self,
        group_id: int,
        user_id: int,
        username: str,
        full_name: str,
        file_id: str,
        file_type: str,
    ) -> PhotoRegistrationStatus:
        return self.status


REGISTER_MESSAGES = {
    "register_photo": {
        "photo_registered": "registered",
        "photo_changed": "changed",
        "photo_not_registered": "not-registered",
    }
}


async def test_internal_register_photo_maps_new_status():
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("group", "Group Name", 999, 0, "group")

    result = await internal_register_photo(
        user,
        chat,
        FakeRegistrationBackend(PhotoRegistrationStatus.NEW),
        Photo("file-id"),
        REGISTER_MESSAGES,
    )

    assert result == "registered"


async def test_internal_register_photo_maps_changed_status():
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("group", "Group Name", 999, 0, "group")

    result = await internal_register_photo(
        user,
        chat,
        FakeRegistrationBackend(PhotoRegistrationStatus.CHANGED),
        Document("file-id"),
        REGISTER_MESSAGES,
    )

    assert result == "changed"


async def test_internal_register_photo_maps_failed_status():
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("group", "Group Name", 999, 0, "group")

    result = await internal_register_photo(
        user,
        chat,
        FakeRegistrationBackend(PhotoRegistrationStatus.FAILED),
        Photo("file-id"),
        REGISTER_MESSAGES,
    )

    assert result == "not-registered"


def test_is_stale_message_accepts_recent_datetime():
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    assert is_stale_message(recent) is False


def test_is_stale_message_rejects_old_datetime():
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    assert is_stale_message(old) is True
