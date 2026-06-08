"""E2E read-путей лидербордов (/leaderboards, /view_all).

Только в групповом чате; в личке хендлеры молчат. Проверяем пустой случай и
вывод победителя.
"""
from __future__ import annotations

from db.db_operations import AdminDB, ObjectFactory

from tests.conftest import feed_message, make_message

GID = 141414
USER = 151
WINNER = 152


def _group_cmd(cmd: str):
    return make_message(cmd, user_id=USER, chat_id=GID, chat_type="supergroup")


async def test_leaderboard_empty(dispatcher, bot, engine, workflow_kwargs):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("LB", GID))

    await feed_message(dispatcher, bot, _group_cmd("/leaderboards"), **workflow_kwargs)

    replies = bot.sent("SendMessage")
    assert replies and "Пока нет данных" in replies[0].text


async def test_leaderboard_lists_winner(dispatcher, bot, engine, workflow_kwargs):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("LB", GID))
    await db.register_user(ObjectFactory.build_user("champ", "Champ", WINNER), GID)
    await db.register_winner(WINNER, GID)

    await feed_message(dispatcher, bot, _group_cmd("/leaderboards"), **workflow_kwargs)

    replies = bot.sent("SendMessage")
    assert replies and "champ" in replies[0].text, "победитель должен попасть в таблицу"
    assert "количество побед: 1" in replies[0].text, "у победителя должна быть ровно 1 победа"


async def test_view_all_ignored_in_private(dispatcher, bot, engine, workflow_kwargs):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("LB", GID))

    # личка: view_overall_participants должен ничего не отвечать
    await feed_message(dispatcher, bot, make_message("/view_all", user_id=USER), **workflow_kwargs)

    assert not bot.sent("SendMessage"), "в личном чате лидерборд не отвечает"


async def test_view_all_empty_in_group(dispatcher, bot, engine, workflow_kwargs):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("LB", GID))

    await feed_message(dispatcher, bot, _group_cmd("/view_all"), **workflow_kwargs)

    replies = bot.sent("SendMessage")
    assert replies and "Пока нет данных" in replies[0].text
