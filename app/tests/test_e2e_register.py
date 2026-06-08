"""E2E регистрации фото в группе (register_photo).

Тот же офлайн-харнесс: реальный Postgres + реальный Dispatcher, мок только
транспорта Telegram. Покрывает основной пользовательский путь «прислать фото
с тегом темы» и все гейты, которые его блокируют (нет совпадения темы,
идёт голосование, старое сообщение).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from db.db_classes import Photo, User, group_photo
from db.db_operations import AdminDB, ObjectFactory

from tests.conftest import (
    count_rows,
    feed_message,
    hashtag_entity,
    make_message,
)

GID = 500500
POSTER = 601
THEME = "#тема"


@pytest.fixture
async def group_with_theme(engine):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Reg Group", GID))
    await db.set_contest_theme(GID, THEME)
    return db


def _photo_msg(caption: str, *, user_id: int = POSTER, file_id: str = "reg-file-1", date=None):
    return make_message(
        caption=caption,
        caption_entities=[hashtag_entity(length=len(THEME))],
        chat_id=GID,
        chat_type="supergroup",
        user_id=user_id,
        username="poster",
        photo_file_id=file_id,
        date=date,
    )


async def test_register_photo_happy_path(dispatcher, bot, engine, workflow_kwargs, group_with_theme, msg):
    await feed_message(dispatcher, bot, _photo_msg(f"{THEME} мой кадр"), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 1, "фото с совпавшим тегом должно зарегистрироваться"
    assert await count_rows(engine, group_photo) == 1, "фото должно быть привязано к группе"
    assert await count_rows(engine, User) == 1, "автор фото должен зарегистрироваться"
    replies = bot.sent("SendMessage")
    assert replies and replies[0].text == msg["register_photo"]["photo_registered"]


async def test_register_photo_rejects_non_matching_tag(dispatcher, bot, engine, workflow_kwargs, group_with_theme):
    # тег есть (фильтр пройден), но это не тема челленджа
    await feed_message(dispatcher, bot, _photo_msg("#другое описание"), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 0, "чужой тег не должен регистрировать фото"
    assert not bot.sent("SendMessage"), "при несовпадении темы хендлер молчит"


async def test_register_photo_blocked_while_vote_in_progress(dispatcher, bot, engine, workflow_kwargs, group_with_theme):
    await group_with_theme.change_current_vote_status(GID)  # голосование активно

    await feed_message(dispatcher, bot, _photo_msg(f"{THEME} поздно"), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 0, "во время голосования приём фоток закрыт"
    assert not bot.sent("SendMessage")


async def test_register_photo_ignores_stale_message(dispatcher, bot, engine, workflow_kwargs, group_with_theme):
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    await feed_message(dispatcher, bot, _photo_msg(f"{THEME} вчерашнее", date=stale), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 0, "сообщения старше 24ч игнорируются"
    assert not bot.sent("SendMessage")


async def test_register_photo_replace_marks_changed(dispatcher, bot, engine, workflow_kwargs, group_with_theme, msg):
    await feed_message(dispatcher, bot, _photo_msg(f"{THEME} первое", file_id="reg-file-A"), **workflow_kwargs)
    bot.clear()

    await feed_message(dispatcher, bot, _photo_msg(f"{THEME} второе", file_id="reg-file-B"), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 1, "повторная отправка заменяет фото, а не добавляет второе"
    photo = await group_with_theme.find_photo_by_user_in_group(POSTER, GID)
    assert photo[1] == "reg-file-B", "file_id должен обновиться на новое фото, а не остаться старым"
    replies = bot.sent("SendMessage")
    assert replies and replies[0].text == msg["register_photo"]["photo_changed"]
