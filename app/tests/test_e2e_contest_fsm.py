"""E2E создания челленджа через FSM (set_theme -> set_theme_accept_message).

Драйвим реальные хендлеры: админский callback «Создать челлендж» -> ввод темы.
add_reminder ходит в Redis, которого в тест-стеке нет, — вызов обёрнут в
try/except в проде, поэтому тема всё равно пишется в БД (это и проверяем).
"""
from __future__ import annotations

from db.db_operations import AdminDB, ObjectFactory
from utils.admin_keyboard import AdminActions

from tests.conftest import feed_callback, feed_message, make_admin_callback, make_message

GID = 121212
ADMIN = 131


async def _seed(engine) -> AdminDB:
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Contest FSM", GID))
    await db.register_admin(ObjectFactory.build_user("boss", "Boss", ADMIN), GID)
    return db


async def test_create_contest_registers_theme(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed(engine)
    assert await db.count_contests(GID) == 0, "по умолчанию только пустой контест '-1'"

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.start_contest_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    await feed_message(dispatcher, bot, make_message("Весна", user_id=ADMIN), **workflow_kwargs)

    assert await db.get_contest_theme(GID) == "#Весна", "введённая тема должна стать активной"
    assert await db.count_contests(GID) == 1
    assert bot.sent("SendMessage"), "бот должен прислать анонс челленджа на подтверждение"
    assert bot.sent("EditMessageText"), "сообщение-приглашение должно отрисоваться"


async def test_create_contest_cancelled(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed(engine)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.start_contest_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    await feed_message(dispatcher, bot, make_message("отмена", user_id=ADMIN), **workflow_kwargs)

    assert await db.count_contests(GID) == 0, "отмена не должна создавать челлендж"
    assert bot.sent("EditMessageText"), "должно прийти сообщение об отмене с кнопкой «Назад»"
