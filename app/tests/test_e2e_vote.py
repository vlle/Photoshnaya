"""E2E приватного флоу голосования — главный сквозной тест.

Прогон: реальный Postgres + реальный Dispatcher со всеми хендлерами,
подделан только транспорт Telegram (MockedBot). VoteBackend на MVP идёт
Python-fallback (GO_API_URL не задан); задашь GO_API_URL + поднимешь
go-api — тот же тест поедет через sidecar без изменений.

Расширять тривиально: seed_active_contest даёт готовый активный челлендж,
make_message/make_callback строят апдейты, bot.sent("...") ловит исходящие
вызовы Telegram, count_rows проверяет БД. Новый сценарий = новая функция
с теми же кубиками (см. test_self_like_is_rejected_e2e).
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from db.db_classes import User, contest_user, photo_like, tmp_photo_like
from db.db_operations import AdminDB, ObjectFactory
from utils.keyboard import Actions, CallbackVote

from tests.conftest import count_rows, feed_callback, feed_message, make_callback, make_message

GROUP_ID = 100100
OWNER_IDS = [201, 202]
VOTER_ID = 301
FILE_IDS = ["e2e-file-1", "e2e-file-2"]


@dataclass
class Seed:
    group_id: int
    voter_id: int
    owner_ids: list[int]
    photo_ids: list[int]
    file_ids: list[str]


@pytest.fixture
async def seed_active_contest(engine) -> Seed:
    """Группа + дефолтный contest + 2 фото разных владельцев + активное голосование."""
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("E2E Group", GROUP_ID))  # создаёт contest
    for i, owner in enumerate(OWNER_IDS):
        await db.register_user(
            ObjectFactory.build_user(f"owner{i + 1}", f"Owner {i + 1}", owner), GROUP_ID
        )
        await db.register_photo_for_contest(owner, GROUP_ID, file_get_id=FILE_IDS[i], type="photo")
    await db.change_current_vote_status(GROUP_ID)  # False -> True
    photo_ids = await db.select_contest_photos_primary_ids(GROUP_ID)
    assert len(photo_ids) == len(FILE_IDS)
    return Seed(GROUP_ID, VOTER_ID, OWNER_IDS, photo_ids, FILE_IDS)


async def test_private_vote_flow_e2e(
    dispatcher, bot, engine, workflow_kwargs, seed_active_contest, msg
):
    s = seed_active_contest
    gid, voter, pids, fids = s.group_id, s.voter_id, s.photo_ids, s.file_ids

    # 1) deep-link /start <gid>_3 -> cmd_start -> get_vote_session -> отправка первого фото
    await feed_message(dispatcher, bot, make_message(f"/start {gid}_3", user_id=voter), **workflow_kwargs)

    photos = bot.sent("SendPhoto")
    assert len(photos) == 1, f"ожидали одно SendPhoto, получили {bot.sent_names()}"
    assert photos[0].chat_id == voter
    assert photos[0].photo == fids[0]                       # первое фото по порядку id
    assert photos[0].caption == msg["vote"]["greeting_message_vote"]
    assert await count_rows(engine, User) == len(OWNER_IDS) + 1, "cmd_start должен зарегистрировать голосующего"

    bot.clear()

    # 2) set_like на первом фото (action 'nl' = 🤍, by-design ставит лайк) -> staged like
    cb_like = CallbackVote(
        action=Actions.no_like_text, current_photo_count="1",
        current_photo_id=str(pids[0]), amount_photos=str(len(pids)), group_id=str(gid),
    )
    await feed_callback(dispatcher, bot, make_callback(cb_like, user_id=voter), **workflow_kwargs)

    assert await count_rows(engine, tmp_photo_like) == 1, "лайк должен осесть в staging-таблицу"
    assert await count_rows(engine, photo_like) == 0, "в постоянную таблицу ещё рано"
    assert bot.sent("EditMessageReplyMarkup"), "клавиатура должна перерисоваться на ❤️"

    bot.clear()

    # 3) submit (action 'f') -> tmp_photo_like -> photo_like + отметка проголосовал
    cb_submit = CallbackVote(
        action=Actions.finish_text, current_photo_count="1",
        current_photo_id=str(pids[0]), amount_photos=str(len(pids)), group_id=str(gid),
    )
    await feed_callback(dispatcher, bot, make_callback(cb_submit, user_id=voter), **workflow_kwargs)

    assert await count_rows(engine, tmp_photo_like) == 0, "staging должен очиститься"
    assert await count_rows(engine, photo_like) == 1, "лайк должен переехать в постоянную таблицу"
    assert await count_rows(engine, contest_user) == 1, "пользователь должен быть отмечен проголосовавшим"
    assert bot.sent("EditMessageMedia")
    assert bot.sent("EditMessageCaption")


async def test_self_like_is_rejected_e2e(
    dispatcher, bot, engine, workflow_kwargs, seed_active_contest, msg
):
    """Расширение того же харнесса: владелец лайкает своё фото -> алерт, ничего не пишется."""
    s = seed_active_contest
    gid, pids = s.group_id, s.photo_ids
    owner_of_first = s.owner_ids[0]

    cb_like = CallbackVote(
        action=Actions.no_like_text, current_photo_count="1",
        current_photo_id=str(pids[0]), amount_photos=str(len(pids)), group_id=str(gid),
    )
    await feed_callback(dispatcher, bot, make_callback(cb_like, user_id=owner_of_first), **workflow_kwargs)

    assert await count_rows(engine, tmp_photo_like) == 0, "self-like не должен записываться"
    answers = bot.sent("AnswerCallbackQuery")
    assert answers and answers[0].show_alert is True
    assert answers[0].text == msg["vote"]["vote_self"]
