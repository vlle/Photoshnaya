"""E2E завершения голосования и выбора победителя (cmd_finish_vote, set_vote).

Самый ценный для уверенности деплоя путь: итог челленджа. Гоняем через
реальные хендлеры + апгрейженный MockedBot (bot.me()/send_photo()/get_url()).
"""
from __future__ import annotations

from db.db_classes import contest_winner, group_photo
from db.db_operations import AdminDB, ObjectFactory
from utils.admin_keyboard import AdminActions
from utils.keyboard import Actions, CallbackVote

from tests.conftest import (
    count_rows,
    feed_callback,
    feed_message,
    make_admin_callback,
    make_callback,
    make_message,
)

GID = 700700
ADMIN = 801
OWNERS = [802, 803]
VOTER = 901
FILE_IDS = ["fin-file-1", "fin-file-2"]
THEME = "#финал"


async def _seed_active_contest(engine) -> AdminDB:
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Finish Group", GID))
    await db.set_contest_theme(GID, THEME)
    for i, owner in enumerate(OWNERS):
        await db.register_user(ObjectFactory.build_user(f"own{i}", f"Own {i}", owner), GID)
        await db.register_photo_for_contest(owner, GID, file_get_id=FILE_IDS[i], type="photo")
    await db.change_current_vote_status(GID)  # активируем голосование
    return db


async def _cast_vote_for_first_photo(dispatcher, bot, engine, workflow_kwargs):
    """Голосующий через реальный флоу ставит лайк первому фото и сабмитит."""
    pids = await AdminDB(engine).select_contest_photos_primary_ids(GID)
    await feed_message(dispatcher, bot, make_message(f"/start {GID}_3", user_id=VOTER), **workflow_kwargs)
    like = CallbackVote(
        action=Actions.no_like_text, current_photo_count="1",
        current_photo_id=str(pids[0]), amount_photos=str(len(pids)), group_id=str(GID),
    )
    await feed_callback(dispatcher, bot, make_callback(like, user_id=VOTER), **workflow_kwargs)
    submit = CallbackVote(
        action=Actions.finish_text, current_photo_count="1",
        current_photo_id=str(pids[0]), amount_photos=str(len(pids)), group_id=str(GID),
    )
    await feed_callback(dispatcher, bot, make_callback(submit, user_id=VOTER), **workflow_kwargs)
    return pids


async def test_finish_vote_picks_single_winner(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_active_contest(engine)
    await _cast_vote_for_first_photo(dispatcher, bot, engine, workflow_kwargs)
    bot.clear()

    await feed_callback(
        dispatcher, bot,
        make_admin_callback(AdminActions.sure_finish_vote_id, GID, user_id=ADMIN),
        **workflow_kwargs,
    )

    assert await count_rows(engine, contest_winner) == 1, "должен зафиксироваться один победитель"
    assert await AdminDB(engine).get_current_vote_status(GID) is False, "голосование должно закрыться"
    assert await count_rows(engine, group_photo) == 0, "фото челленджа должны быть очищены"

    win_photos = [p for p in bot.sent("SendPhoto") if p.chat_id == GID]
    assert len(win_photos) == 1, "фото победителя должно уйти одним SendPhoto в группу"
    assert win_photos[0].photo == FILE_IDS[0], "победило первое фото (за него голос)"
    expected_caption = msg["vote"]["user_info"].format(
        theme=THEME, username="own0", full_name="Own 0", likes=1
    )
    assert win_photos[0].caption == expected_caption, "подпись победителя должна содержать тему, ник и число лайков"
    edits = bot.sent("EditMessageText")
    assert any(e.text == msg["admin"]["vote_end"] for e in edits)


async def test_finish_vote_no_winner_when_nobody_voted(dispatcher, bot, engine, workflow_kwargs, msg):
    await _seed_active_contest(engine)  # фото есть, голосов нет
    bot.clear()

    await feed_callback(
        dispatcher, bot,
        make_admin_callback(AdminActions.sure_finish_vote_id, GID, user_id=ADMIN),
        **workflow_kwargs,
    )

    assert await count_rows(engine, contest_winner) == 0
    assert not [p for p in bot.sent("SendPhoto") if p.chat_id == GID], "без голосов фото победителя не шлём"
    edits = bot.sent("EditMessageText")
    assert any(e.text == msg["vote"]["no_winner"] for e in edits)
    assert await count_rows(engine, group_photo) == 0, "фото должны быть стёрты и при отсутствии победителя"
    assert await AdminDB(engine).get_current_vote_status(GID) is False, "голосование должно закрыться даже без победителя"


async def test_finish_vote_no_photos(dispatcher, bot, engine, workflow_kwargs, msg):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Empty Finish", GID))
    await db.set_contest_theme(GID, THEME)
    await db.change_current_vote_status(GID)
    bot.clear()

    await feed_callback(
        dispatcher, bot,
        make_admin_callback(AdminActions.sure_finish_vote_id, GID, user_id=ADMIN),
        **workflow_kwargs,
    )

    assert await count_rows(engine, contest_winner) == 0
    edits = bot.sent("EditMessageText")
    assert any(e.text == msg["admin"]["no_photos_at_end"] for e in edits)
    assert await db.get_current_vote_status(GID) is False, "голосование должно закрыться и при отсутствии фото"


async def test_set_vote_activates_voting(dispatcher, bot, engine, workflow_kwargs, msg):
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Start Vote", GID))
    await db.set_contest_theme(GID, THEME)
    await db.register_user(ObjectFactory.build_user("own0", "Own 0", OWNERS[0]), GID)
    await db.register_photo_for_contest(OWNERS[0], GID, file_get_id=FILE_IDS[0], type="photo")
    assert await db.get_current_vote_status(GID) is False

    await feed_callback(
        dispatcher, bot,
        make_admin_callback(AdminActions.sure_start_vote_id, GID, user_id=ADMIN),
        **workflow_kwargs,
    )

    assert await db.get_current_vote_status(GID) is True, "set_vote должен включить голосование"
    edits = bot.sent("EditMessageText")
    assert edits and msg["vote"]["will_you_post"] in edits[0].text, "должен прийти текст-приглашение с анонсом"
