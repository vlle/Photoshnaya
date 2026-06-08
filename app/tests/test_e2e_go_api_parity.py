"""E2E-паритет реального go-api sidecar с Python-fallback.

Прод ходит в go-api, а остальные e2e — по fallback (GO_API_URL не задан). Этот
модуль гоняет тот же сценарий голосования ЧЕРЕЗ настоящий go-api (тот же
Postgres) и проверяет, что состояние БД и бизнес-ошибки совпадают с fallback —
ловит «тихую дивергенцию», от которой circuit-breaker не спасает.

Запускается только когда go-api поднят в стеке (docker-compose.test.yml задаёт
GO_API_URL_TEST). Вне стека — скипается, поэтому не ломает локальный pytest.
"""
from __future__ import annotations

import os

import pytest

from db.db_classes import contest_user, photo_like, tmp_photo_like
from db.db_operations import AdminDB, ObjectFactory
from services.vote_backend import VoteBackend, VoteBackendBusinessError

from tests.conftest import count_rows

API_URL = os.environ.get("GO_API_URL_TEST")

pytestmark = pytest.mark.skipif(
    not API_URL, reason="GO_API_URL_TEST не задан — go-api нет в стеке"
)

GID = 222333
OWNERS = [241, 242]
VOTER = 251
FILE_IDS = ["parity-1", "parity-2"]


async def _seed(engine, *, active: bool = True, with_photos: bool = True) -> AdminDB:
    db = AdminDB(engine)
    await db.register_group(ObjectFactory.build_group("Parity", GID))
    await db.register_user(ObjectFactory.build_user("voter", "V", VOTER), GID)
    if with_photos:
        for i, owner in enumerate(OWNERS):
            await db.register_user(ObjectFactory.build_user(f"o{i}", f"O{i}", owner), GID)
            await db.register_photo_for_contest(owner, GID, file_get_id=FILE_IDS[i], type="photo")
    if active:
        await db.change_current_vote_status(GID)
    return db


async def _backend(engine) -> VoteBackend:
    be = VoteBackend(engine, api_url=API_URL)
    await be.start()
    return be


async def test_go_api_vote_flow_matches_fallback(engine):
    db = await _seed(engine)
    pids = await db.select_contest_photos_primary_ids(GID)
    be = await _backend(engine)
    try:
        session = await be.get_vote_session(GID, VOTER)
        assert session.photo_id == pids[0], "go-api должен отдать первое фото по порядку"
        assert session.total_photos == 2

        await be.set_like(GID, VOTER, pids[0])
        assert await count_rows(engine, tmp_photo_like) == 1, "go-api стейджит лайк так же, как fallback"
        assert await count_rows(engine, photo_like) == 0

        await be.submit_vote(GID, VOTER)
        assert await count_rows(engine, tmp_photo_like) == 0
        assert await count_rows(engine, photo_like) == 1
        assert await count_rows(engine, contest_user) == 1
    finally:
        await be.close()


async def test_go_api_browse_next_prev(engine):
    db = await _seed(engine)
    pids = await db.select_contest_photos_primary_ids(GID)
    be = await _backend(engine)
    try:
        nxt = await be.get_next_vote_photo(GID, VOTER, pids[0])
        assert nxt.photo_id == pids[1] and nxt.current_index == 2
        prev = await be.get_prev_vote_photo(GID, VOTER, pids[1])
        assert prev.photo_id == pids[0] and prev.current_index == 1
    finally:
        await be.close()


async def test_go_api_self_like_rejected(engine):
    db = await _seed(engine)
    pids = await db.select_contest_photos_primary_ids(GID)
    be = await _backend(engine)
    try:
        with pytest.raises(VoteBackendBusinessError) as ei:
            await be.set_like(GID, OWNERS[0], pids[0])  # владелец лайкает своё
        assert ei.value.code == "self_like"
        assert await count_rows(engine, tmp_photo_like) == 0
    finally:
        await be.close()


async def test_go_api_already_voted(engine):
    db = await _seed(engine)
    pids = await db.select_contest_photos_primary_ids(GID)
    be = await _backend(engine)
    try:
        await be.set_like(GID, VOTER, pids[0])
        await be.submit_vote(GID, VOTER)
        with pytest.raises(VoteBackendBusinessError) as ei:
            await be.get_vote_session(GID, VOTER)
        assert ei.value.code == "already_voted"
    finally:
        await be.close()


async def test_go_api_no_vote_yet(engine):
    await _seed(engine, active=False)
    be = await _backend(engine)
    try:
        with pytest.raises(VoteBackendBusinessError) as ei:
            await be.get_vote_session(GID, VOTER)
        assert ei.value.code == "no_vote_yet"
    finally:
        await be.close()


async def test_go_api_no_photos(engine):
    await _seed(engine, with_photos=False, active=True)
    be = await _backend(engine)
    try:
        with pytest.raises(VoteBackendBusinessError) as ei:
            await be.get_vote_session(GID, VOTER)
        assert ei.value.code == "no_photos"
    finally:
        await be.close()
