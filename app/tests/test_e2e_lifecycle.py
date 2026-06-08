"""E2E полного жизненного цикла челленджа через реальные хендлеры.

Один сквозной сценарий, имитирующий продакшен-путь целиком:
бот вступает в группу -> задаётся тема -> участники присылают фото ->
админ запускает голосование -> зрители голосуют -> админ завершает ->
определяется победитель. Если этот тест зелёный — основной продукт работает
end-to-end. Отдельные тесты покрывают ветки и ошибки; этот — связность.
"""
from __future__ import annotations

from db.db_classes import Photo, contest_winner, group_photo
from db.db_operations import AdminDB
from utils.admin_keyboard import AdminActions
from utils.keyboard import Actions, CallbackVote

from tests.conftest import (
    count_rows,
    feed_callback,
    feed_chat_member,
    feed_message,
    hashtag_entity,
    make_admin_callback,
    make_callback,
    make_chat_member_updated,
    make_message,
)

GID = 161616
ADMIN = 171
OWNERS = [181, 182]
VOTERS = [191, 192]
THEME = "#лето"


def _photo_msg(owner: int, file_id: str):
    return make_message(
        caption=f"{THEME} работа",
        caption_entities=[hashtag_entity(length=len(THEME))],
        chat_id=GID,
        chat_type="supergroup",
        user_id=owner,
        username=f"owner{owner}",
        photo_file_id=file_id,
    )


async def _vote_for(dispatcher, bot, workflow_kwargs, voter: int, photo_id: int, total: int):
    await feed_message(dispatcher, bot, make_message(f"/start {GID}_3", user_id=voter), **workflow_kwargs)
    like = CallbackVote(
        action=Actions.no_like_text, current_photo_count="1",
        current_photo_id=str(photo_id), amount_photos=str(total), group_id=str(GID),
    )
    await feed_callback(dispatcher, bot, make_callback(like, user_id=voter), **workflow_kwargs)
    submit = CallbackVote(
        action=Actions.finish_text, current_photo_count="1",
        current_photo_id=str(photo_id), amount_photos=str(total), group_id=str(GID),
    )
    await feed_callback(dispatcher, bot, make_callback(submit, user_id=voter), **workflow_kwargs)


async def test_full_contest_lifecycle(dispatcher, bot, engine, workflow_kwargs):
    db = AdminDB(engine)

    # 1) бота добавили в группу -> группа + админ
    await feed_chat_member(
        dispatcher, bot, make_chat_member_updated(actor_id=ADMIN, chat_id=GID, chat_title="Summer Club"),
        **workflow_kwargs,
    )
    assert await db.check_admin(ADMIN, GID) is True

    # 2) задаём тему челленджа (FSM создания темы покрыт отдельным тестом)
    await db.set_contest_theme(GID, THEME)

    # 3) два участника присылают фото с тегом темы
    await feed_message(dispatcher, bot, _photo_msg(OWNERS[0], "life-1"), **workflow_kwargs)
    await feed_message(dispatcher, bot, _photo_msg(OWNERS[1], "life-2"), **workflow_kwargs)
    assert await count_rows(engine, Photo) == 2
    assert await count_rows(engine, group_photo) == 2, "обе работы должны быть привязаны к группе"
    pids = await db.select_contest_photos_primary_ids(GID)

    # 4) админ запускает голосование
    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.sure_start_vote_id, GID, user_id=ADMIN), **workflow_kwargs
    )
    assert await db.get_current_vote_status(GID) is True

    # 5) оба зрителя голосуют за первое фото
    await _vote_for(dispatcher, bot, workflow_kwargs, VOTERS[0], pids[0], len(pids))
    await _vote_for(dispatcher, bot, workflow_kwargs, VOTERS[1], pids[0], len(pids))
    bot.clear()

    # 6) админ завершает голосование -> победитель
    await feed_callback(
        dispatcher, bot, make_admin_callback(AdminActions.sure_finish_vote_id, GID, user_id=ADMIN), **workflow_kwargs
    )

    assert await count_rows(engine, contest_winner) == 1, "должен определиться один победитель"
    assert await db.get_current_vote_status(GID) is False, "голосование закрыто"
    assert await count_rows(engine, group_photo) == 0, "работы челленджа очищены"
    win_photos = [p for p in bot.sent("SendPhoto") if p.chat_id == GID]
    assert win_photos and win_photos[0].photo == "life-1", "победило первое фото (2 голоса)"
