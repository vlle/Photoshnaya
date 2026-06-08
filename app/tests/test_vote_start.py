import pytest

from handlers.internal_logic.vote_start import internal_start
from services.vote_backend import VoteBackendBusinessError, VotePhotoState
from utils.TelegramUserClass import TelegramChat, TelegramUser


class FakeVoteBackend:
    def __init__(self, state=None, err=None):
        self.state = state
        self.err = err

    async def get_vote_session(self, group_id: int, user_id: int):
        if self.err:
            raise self.err
        return self.state


@pytest.mark.parametrize(
    ("backend_error", "expected_text"),
    [
        (VoteBackendBusinessError("no_photos"), "Фотографий с таким тегом нет"),
        (VoteBackendBusinessError("no_vote_yet"), "Эта голосовалка неактивна"),
        (
            VoteBackendBusinessError("already_voted"),
            "Ты уже проголосовал в этом челлендже",
        ),
    ],
)
async def test_internal_start_maps_sidecar_errors(backend_error, expected_text):
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("private", "private", 999, 0, "private")

    text, err, vote_session = await internal_start(
        chat, user, "/start 100_3", FakeVoteBackend(err=backend_error)
    )

    assert text == expected_text
    assert err is True
    assert vote_session is None


async def test_internal_start_rejects_non_numeric_group():
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("private", "private", 999, 0, "private")

    text, err, vote_session = await internal_start(
        chat, user, "/start abc_3", FakeVoteBackend()
    )

    assert text == "Неверная ссылка"
    assert err is True
    assert vote_session is None


async def test_internal_start_returns_vote_session():
    user = TelegramUser("user", "User Name", 101, 0, 1)
    chat = TelegramChat("private", "private", 999, 0, "private")
    expected_state = VotePhotoState(
        group_id=100,
        photo_id=55,
        file_id="file-id",
        file_type="photo",
        current_index=1,
        total_photos=3,
        liked_state=0,
    )

    text, err, vote_session = await internal_start(
        chat, user, "/start 100_3", FakeVoteBackend(state=expected_state)
    )

    assert text == "Начинай голосовать! Можно за несколько фотографий."
    assert err is False
    assert vote_session == expected_state
