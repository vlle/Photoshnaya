"""E2E админ-меню: выбор группы, отрисовка действий, просмотр работ/голосов, назад.

Эти пути читают результаты bot.me()/get_chat_member/send_* — работают благодаря
каноничным ответам MockedBot. cmd_finish_vote/set_vote покрыты отдельно.
"""
from __future__ import annotations

from db.db_operations import AdminDB, ObjectFactory
from utils.admin_keyboard import AdminActions

from tests.conftest import feed_callback, feed_message, make_admin_callback, make_message

GID = 808080
ADMIN = 811
OWNERS = [812, 813]
FILE_IDS = ["adm-file-1", "adm-file-2"]
THEME = "#тема"


async def _seed_group_with_admin(engine, *, with_theme=True) -> AdminDB:
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Admin Group", GID))
    await db.register_admin(ObjectFactory.build_user("boss", "Boss", ADMIN), GID)
    if with_theme:
        await db.set_contest_theme(GID, THEME)
    return db


async def _seed_two_photos(db: AdminDB):
    for i, owner in enumerate(OWNERS):
        await db.register_user(ObjectFactory.build_user(f"own{i}", f"Own {i}", owner), GID)
        await db.register_photo_for_contest(owner, GID, file_get_id=FILE_IDS[i], type="photo")


async def test_choose_group_rejects_non_admin(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_group_with_admin(engine)

    await feed_message(dispatcher, bot, make_message("/admin", user_id=999111), **workflow_kwargs)

    sent = bot.sent("SendMessage")
    assert sent and sent[0].text == msg["admin"]["you_are_not_admin"]


async def test_choose_group_lists_admin_groups(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_group_with_admin(engine)

    await feed_message(dispatcher, bot, make_message("/admin", user_id=ADMIN), **workflow_kwargs)

    sent = bot.sent("SendMessage")
    assert sent and sent[0].text == msg["admin"]["choose_group"]
    assert sent[0].reply_markup is not None, "должна прийти клавиатура со списком групп"


async def test_action_choose_renders_board(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_group_with_admin(engine)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.chosen_group, GID, user_id=ADMIN), **workflow_kwargs
    )

    edits = bot.sent("EditMessageText")
    assert edits, "меню действий должно отрисоваться через edit_text"
    assert edits[0].reply_markup is not None
    assert msg["admin"]["choose_action"] in edits[0].text
    # тема есть, голосование выключено, не владелец -> доска keyboard_no_vote
    texts = [b.text for row in edits[0].reply_markup.inline_keyboard for b in row]
    assert AdminActions.finish_contest_text in texts, "должна быть кнопка «Начать голосование»"
    assert AdminActions.finish_vote_text not in texts, "кнопки завершения быть не должно — голосование не идёт"


async def test_view_submissions_empty(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_group_with_admin(engine)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.view_submissions_id, GID, user_id=ADMIN), **workflow_kwargs
    )

    edits = bot.sent("EditMessageText")
    assert any(e.text == msg["admin"]["no_photos_at_start"] for e in edits)


async def test_view_submissions_sends_media(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed_group_with_admin(engine)
    await _seed_two_photos(db)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.view_submissions_id, GID, user_id=ADMIN), **workflow_kwargs
    )

    groups = bot.sent("SendMediaGroup")
    assert groups and groups[0].chat_id == ADMIN, "две работы уходят альбомом админу"
    assert len(groups[0].media) == 2
    assert {m.media for m in groups[0].media} == set(FILE_IDS), "в альбоме должны быть оба загруженных фото"
    assert all(m.type == "photo" for m in groups[0].media)


async def test_view_votes_sends_media(dispatcher, bot, engine, workflow_kwargs):
    db = await _seed_group_with_admin(engine)
    await _seed_two_photos(db)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.view_votes_id, GID, user_id=ADMIN), **workflow_kwargs
    )

    groups = bot.sent("SendMediaGroup")
    assert groups and groups[0].chat_id == ADMIN
    assert {m.media for m in groups[0].media} == set(FILE_IDS), "должны показаться обе работы"


async def test_callback_back_returns_to_group_list(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_group_with_admin(engine)

    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.back, GID, user_id=ADMIN), **workflow_kwargs
    )

    edits = bot.sent("EditMessageText")
    assert edits and edits[0].text == msg["admin"]["choose_group"]
    assert edits[0].reply_markup and len(edits[0].reply_markup.inline_keyboard) >= 1, "в списке должна быть группа"
