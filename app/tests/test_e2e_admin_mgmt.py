"""E2E админ-управления через FSM: добавить/удалить админа, удалить фото.

Каждый флоу: админский callback переводит FSM в нужное состояние, затем
сообщение (пересланное или @username) доводит действие до записи в БД.
"""
from __future__ import annotations

from aiogram.types import User as TgUser

from db.db_classes import Photo, group_admin
from db.db_operations import AdminDB, ObjectFactory
from utils.admin_keyboard import AdminActions

from tests.conftest import count_rows, feed_callback, feed_message, make_admin_callback, make_message

GID = 909090
ADMIN = 921
NEW_ADMIN = 922
VICTIM = 923


async def _seed_group_with_admin(engine) -> AdminDB:
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Mgmt Group", GID))
    await db.register_admin(ObjectFactory.build_user("boss", "Boss", ADMIN), GID)
    return db


def _forwarded(text: str, *, from_id: int, username: str, full_name: str, actor: int):
    return make_message(
        text=text,
        user_id=actor,
        forward_from=TgUser(id=from_id, is_bot=False, first_name=full_name, username=username),
    )


async def test_add_admin_flow(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed_group_with_admin(engine)
    assert await db.check_admin(NEW_ADMIN, GID) is False

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.add_admin_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    await feed_message(
        dispatcher, bot,
        _forwarded("go", from_id=NEW_ADMIN, username="newadm", full_name="New Adm", actor=ADMIN),
        **workflow_kwargs,
    )

    assert await db.check_admin(NEW_ADMIN, GID) is True, "пересланный юзер должен стать админом"


async def test_add_admin_cancelled(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed_group_with_admin(engine)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.add_admin_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    # текст «отмена» без пересланного сообщения -> отмена
    await feed_message(dispatcher, bot, make_message("отмена", user_id=ADMIN), **workflow_kwargs)

    assert await db.check_admin(NEW_ADMIN, GID) is False
    assert await count_rows(engine, group_admin) == 1, "должен остаться только исходный админ"


async def test_del_admin_flow(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed_group_with_admin(engine)
    await db.register_admin(ObjectFactory.build_user("victim", "Victim", NEW_ADMIN), GID)
    assert await db.check_admin(NEW_ADMIN, GID) is True

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.delete_admin_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    await feed_message(
        dispatcher, bot,
        _forwarded("go", from_id=NEW_ADMIN, username="victim", full_name="Victim", actor=ADMIN),
        **workflow_kwargs,
    )

    assert await db.check_admin(NEW_ADMIN, GID) is False, "пересланный админ должен лишиться прав"


async def test_delete_submission_by_username(dispatcher, bot, engine, workflow_kwargs, msg):
    db = await _seed_group_with_admin(engine)
    await db.register_user(ObjectFactory.build_user("victim", "Victim", VICTIM), GID)
    await db.register_photo_for_contest(VICTIM, GID, file_get_id="del-file-1", type="photo")
    assert await count_rows(engine, Photo) == 1

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.delete_submission_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    # шаг 1: указываем владельца по @username -> бот шлёт фото на подтверждение
    await feed_message(dispatcher, bot, make_message("@victim", user_id=ADMIN), **workflow_kwargs)
    confirm_photos = bot.sent("SendPhoto")
    assert confirm_photos and confirm_photos[0].photo == "del-file-1", "на подтверждение показывают именно фото жертвы"

    # шаг 2: подтверждаем удаление
    await feed_message(dispatcher, bot, make_message("Да", user_id=ADMIN), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 0, "подтверждённое фото должно удалиться"
    replies = bot.sent("SendMessage")
    assert any(r.text == msg["delete_photo"]["del_photo"] for r in replies)


async def test_delete_submission_cancelled_keeps_photo(dispatcher, bot, engine, workflow_kwargs, msg):
    db = await _seed_group_with_admin(engine)
    await db.register_user(ObjectFactory.build_user("victim", "Victim", VICTIM), GID)
    await db.register_photo_for_contest(VICTIM, GID, file_get_id="del-file-2", type="photo")

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.delete_submission_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    await feed_message(dispatcher, bot, make_message("@victim", user_id=ADMIN), **workflow_kwargs)
    await feed_message(dispatcher, bot, make_message("Нет", user_id=ADMIN), **workflow_kwargs)

    assert await count_rows(engine, Photo) == 1, "при отказе фото остаётся"
    replies = bot.sent("SendMessage")
    assert any(r.text == msg["delete_photo"]["cancel_del"] for r in replies), "должно прийти сообщение об отмене"
