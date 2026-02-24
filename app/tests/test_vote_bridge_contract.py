import pytest

from handlers import personal_vote_menu
from utils.keyboard import CallbackVote


class FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


class FakeMessage:
    def __init__(self, user_id: int):
        self.from_user = FakeUser(user_id)
        self.reply_markup_calls = []
        self.media_calls = []
        self.caption_calls = []

    async def edit_reply_markup(self, reply_markup=None):
        self.reply_markup_calls.append(reply_markup)

    async def edit_media(self, media=None, reply_markup=None):
        self.media_calls.append({"media": media, "reply_markup": reply_markup})

    async def edit_caption(self, caption=None):
        self.caption_calls.append(caption)


class FakeQuery:
    def __init__(self, user_id: int):
        self.from_user = FakeUser(user_id)
        self.message = FakeMessage(user_id)
        self.answers = []

    async def answer(self, text: str, show_alert: bool = False):
        self.answers.append({"text": text, "show_alert": show_alert})


class FakeLikeEngine:
    def __init__(self, like_result: int = 0):
        self.like_result = like_result
        self.like_calls = 0
        self.insert_all_likes_calls = 0
        self.delete_tmp_calls = 0
        self.engine = object()

    async def like_photo(self, user_id: int, photo_id: int):
        self.like_calls += 1
        return self.like_result

    async def insert_all_likes(self, user_id: int, group_id: int):
        self.insert_all_likes_calls += 1

    async def delete_likes_from_tmp_vote(self, user_id: int, group_id: int):
        self.delete_tmp_calls += 1


def callback_payload() -> CallbackVote:
    return CallbackVote(
        action="l",
        current_photo_count="1",
        current_photo_id="10",
        amount_photos="2",
        group_id="100",
    )


@pytest.mark.asyncio
async def test_vote_bridge_disabled_falls_back_to_legacy_like(monkeypatch):
    monkeypatch.setenv(personal_vote_menu.FEATURE_GO_VOTE_FLOW, "false")

    query = FakeQuery(user_id=42)
    like_engine = FakeLikeEngine(like_result=0)

    await personal_vote_menu.callback_set_like(
        query=query,
        callback_data=callback_payload(),
        like_engine=like_engine,
        msg={"vote": {"vote_self": "Нельзя лайкать себя"}},
    )

    assert like_engine.like_calls == 1
    assert len(query.message.reply_markup_calls) == 1


@pytest.mark.asyncio
async def test_vote_bridge_enabled_success_skips_legacy_like(monkeypatch):
    monkeypatch.setenv(personal_vote_menu.FEATURE_GO_VOTE_FLOW, "true")

    async def fake_bridge(path, payload):
        return {
            "status": "ok",
            "code": "like_set",
            "state": {
                "group_id": 100,
                "amount_photos": 2,
                "current_photo_id": 10,
                "current_photo_count": 1,
                "is_liked_photo": 1,
                "media_type": "photo",
                "media_file_id": "file-id",
            },
        }

    monkeypatch.setattr(personal_vote_menu, "_call_vote_bridge", fake_bridge)

    query = FakeQuery(user_id=42)
    like_engine = FakeLikeEngine(like_result=0)

    await personal_vote_menu.callback_set_like(
        query=query,
        callback_data=callback_payload(),
        like_engine=like_engine,
        msg={"vote": {"vote_self": "Нельзя лайкать себя"}},
    )

    assert like_engine.like_calls == 0
    assert len(query.message.reply_markup_calls) == 1


@pytest.mark.asyncio
async def test_vote_bridge_enabled_failure_falls_back_to_legacy_like(monkeypatch):
    monkeypatch.setenv(personal_vote_menu.FEATURE_GO_VOTE_FLOW, "true")

    async def fake_bridge(path, payload):
        return None

    monkeypatch.setattr(personal_vote_menu, "_call_vote_bridge", fake_bridge)

    query = FakeQuery(user_id=42)
    like_engine = FakeLikeEngine(like_result=0)

    await personal_vote_menu.callback_set_like(
        query=query,
        callback_data=callback_payload(),
        like_engine=like_engine,
        msg={"vote": {"vote_self": "Нельзя лайкать себя"}},
    )

    assert like_engine.like_calls == 1
    assert len(query.message.reply_markup_calls) == 1


@pytest.mark.asyncio
async def test_vote_submit_bridge_success_skips_legacy_commit(monkeypatch):
    monkeypatch.setenv(personal_vote_menu.FEATURE_GO_VOTE_FLOW, "true")

    async def fake_bridge(path, payload):
        return {"status": "ok", "code": "thanks_for_vote"}

    monkeypatch.setattr(personal_vote_menu, "_call_vote_bridge", fake_bridge)

    query = FakeQuery(user_id=42)
    like_engine = FakeLikeEngine(like_result=0)

    await personal_vote_menu.callback_send_vote(
        query=query,
        callback_data=callback_payload(),
        like_engine=like_engine,
        msg={"vote": {"thanks_for_vote": "Спасибо за голос"}},
    )

    assert like_engine.insert_all_likes_calls == 0
    assert like_engine.delete_tmp_calls == 0
    assert len(query.message.media_calls) == 1
    assert query.message.caption_calls == ["Спасибо за голос"]
