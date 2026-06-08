"""Общие фикстуры для e2e-тестов бота.

Граница e2e: реальный Postgres + реальный aiogram Dispatcher со всеми
хендлерами/FSM; подделан только транспорт к Telegram (MockedBot).
VoteBackend идёт в go-api, если задан GO_API_URL, иначе — Python-fallback
поверх той же engine. На MVP GO_API_URL не задан → проверяется fallback-путь.
"""
from __future__ import annotations

import os
import pathlib
import tomllib
from datetime import datetime, timezone
from typing import Any

import pytest
from aiogram import Bot, Dispatcher, F
from aiogram.filters import (
    JOIN_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
)
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from db.db_classes import Base
from db.db_operations import AdminDB, ObjectFactory, RegisterDB
from services.vote_backend import VoteBackend

# --- хендлеры/фильтры: импорт 1:1 с app/bot.py ---
from handlers.admin_add_fsm import AdminAdd, set_admin, set_admin_accept_message
from handlers.admin_del_fsm import AdminDel, del_admin, del_admin_accept_message
from handlers.admin_handler import (
    callback_back,
    cmd_action_choose,
    cmd_check_if_sure,
    cmd_check_if_sure_vote,
    cmd_choose_group,
    cmd_finish_vote,
    view_submissions,
    view_votes,
)
from handlers.contest_fsm import (
    ContestCreate,
    set_theme,
    set_theme_accept_message,
    should_i_post_theme,
)
from handlers.delete_submission import (
    DeletePhoto,
    delete_photo_r_u_sure,
    delete_submission,
    make_delete_decision,
    set_admin_delete_photo,
)
from handlers.on_join import on_user_join
from handlers.personal_vote_menu import (
    callback_next,
    callback_prev,
    callback_send_vote,
    callback_set_like,
    callback_set_no_like,
    callback_vote_self,
    cmd_start,
    get_file_id,
)
from handlers.user_action import register_photo, view_leaders, view_overall_participants
from handlers.vote_start_fsm import VoteStart, set_vote, should_i_post_vote
from utils.admin_keyboard import AdminActions, CallbackManage
from utils.keyboard import Actions, CallbackVote

from tests.mocked_bot import MockedBot


def register_handlers(dp: Dispatcher) -> None:
    """Регистрация всех хендлеров — зеркало app/bot.py:101-189.

    Держим в синхроне с bot.py: новый хендлер в боте -> строка здесь,
    тогда e2e-тесты ловят дрейф маршрутизации.
    """
    dp.message.register(register_photo, F.caption_entities & ~(F.chat.type == "private"))
    dp.message.register(get_file_id, Command(commands=["get_file_id"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.my_chat_member.register(
        on_user_join, ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
    )

    dp.callback_query.register(callback_next, CallbackVote.filter(F.action == Actions.next_text))
    dp.callback_query.register(callback_prev, CallbackVote.filter(F.action == Actions.prev_text))
    dp.callback_query.register(callback_set_like, CallbackVote.filter(F.action == Actions.no_like_text))
    dp.callback_query.register(callback_set_no_like, CallbackVote.filter(F.action == Actions.like_text))
    dp.callback_query.register(callback_vote_self, CallbackVote.filter(F.action == Actions.like_self))
    dp.callback_query.register(callback_send_vote, CallbackVote.filter(F.action == Actions.finish_text))

    dp.message.register(cmd_choose_group, Command(commands=["admin"]))
    dp.message.register(view_leaders, Command(commands=["leaderboards"]))
    dp.message.register(view_overall_participants, Command(commands=["view_all"]))
    dp.callback_query.register(callback_back, CallbackManage.filter(F.action == AdminActions.back))
    dp.callback_query.register(cmd_action_choose, CallbackManage.filter(F.action == AdminActions.chosen_group))
    dp.callback_query.register(cmd_check_if_sure_vote, CallbackManage.filter(F.action == AdminActions.finish_contest_id))
    dp.callback_query.register(set_vote, CallbackManage.filter(F.action == AdminActions.sure_start_vote_id))
    dp.callback_query.register(view_submissions, CallbackManage.filter(F.action == AdminActions.view_submissions_id))
    dp.callback_query.register(view_votes, CallbackManage.filter(F.action == AdminActions.view_votes_id))
    dp.callback_query.register(cmd_check_if_sure, CallbackManage.filter(F.action == AdminActions.finish_vote_id))
    dp.callback_query.register(cmd_finish_vote, CallbackManage.filter(F.action == AdminActions.sure_finish_vote_id))
    dp.callback_query.register(delete_submission, CallbackManage.filter(F.action == AdminActions.delete_submission_id))
    dp.callback_query.register(set_theme, CallbackManage.filter(F.action == AdminActions.start_contest_id))
    dp.callback_query.register(set_admin, CallbackManage.filter(F.action == AdminActions.add_admin_id))
    dp.callback_query.register(del_admin, CallbackManage.filter(F.action == AdminActions.delete_admin_id))

    dp.message.register(set_theme_accept_message, ContestCreate.name_contest)
    dp.message.register(should_i_post_theme, ContestCreate.will_you_post)
    dp.message.register(should_i_post_vote, VoteStart.will_you_post)
    dp.message.register(set_admin_accept_message, AdminAdd.send_admin)
    dp.message.register(del_admin_accept_message, AdminDel.send_admin)
    dp.message.register(set_admin_delete_photo, DeletePhoto.send_photo_owner)
    dp.message.register(delete_photo_r_u_sure, DeletePhoto.are_you_sure)
    dp.message.register(make_delete_decision, DeletePhoto.wait_for_confirmation)


# ----------------------------- фикстуры -----------------------------

@pytest.fixture
async def engine() -> AsyncEngine:
    ps_url = os.environ.get("testps_url")
    if not ps_url:
        pytest.skip("testps_url not set")
    eng = create_async_engine(ps_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def msg() -> dict:
    # app/tests/conftest.py -> app/handlers/handlers_text/text.toml
    app_dir = pathlib.Path(__file__).resolve().parent.parent
    text_toml = app_dir / "handlers" / "handlers_text" / "text.toml"
    with open(text_toml, "rb") as f:
        return tomllib.load(f)


@pytest.fixture
async def like_engine(engine) -> VoteBackend:
    be = VoteBackend(engine, api_url=os.environ.get("GO_API_URL"))
    await be.start()
    yield be
    await be.close()


@pytest.fixture
def bot() -> MockedBot:
    return MockedBot()


@pytest.fixture
def dispatcher() -> Dispatcher:
    dp = Dispatcher()
    register_handlers(dp)
    return dp


@pytest.fixture
def workflow_kwargs(engine, like_engine, msg) -> dict[str, Any]:
    """DI, идентичный dp.start_polling(**kwargs) в bot.py:209-217."""
    return dict(
        engine=engine,
        register_unit=RegisterDB(engine),
        obj_factory=ObjectFactory(),
        admin_unit=AdminDB(engine),
        like_engine=like_engine,
        msg=msg,
    )


# ------------------------- билдеры апдейтов -------------------------

class _Seq:
    def __init__(self) -> None:
        self.n = 1000

    def __call__(self) -> int:
        self.n += 1
        return self.n


next_id = _Seq()


def make_message(
    text: str | None = None,
    *,
    user_id: int,
    chat_id: int | None = None,
    chat_type: str = "private",
    username: str | None = "voter",
    first_name: str = "V",
    caption: str | None = None,
    photo_file_id: str | None = None,
) -> Message:
    from aiogram.types import PhotoSize

    photo = None
    if photo_file_id is not None:
        photo = [PhotoSize(file_id=photo_file_id, file_unique_id=photo_file_id, width=1, height=1)]
    return Message(
        message_id=next_id(),
        date=datetime.now(timezone.utc),  # свежая дата: is_stale_message режет >24h
        chat=Chat(id=chat_id if chat_id is not None else user_id, type=chat_type),
        from_user=User(id=user_id, is_bot=False, first_name=first_name, username=username),
        text=text,
        caption=caption,
        photo=photo,
    )


def make_callback(cb: CallbackVote, *, user_id: int, on_message: Message | None = None) -> CallbackQuery:
    bot_user = User(id=42, is_bot=True, first_name="bot", username="bot")
    kb_msg = on_message or Message(
        message_id=next_id(),
        date=datetime.now(timezone.utc),
        chat=Chat(id=user_id, type="private"),
        from_user=bot_user,  # сообщение с клавиатурой — от бота
        text="kb",
    )
    return CallbackQuery(
        id=str(next_id()),
        from_user=User(id=user_id, is_bot=False, first_name="V", username="voter"),
        chat_instance="ci",
        message=kb_msg,
        data=cb.pack(),
    )


async def feed_message(dp: Dispatcher, bot: Bot, message: Message, **wf) -> Any:
    return await dp.feed_update(bot, Update(update_id=next_id(), message=message), **wf)


async def feed_callback(dp: Dispatcher, bot: Bot, query: CallbackQuery, **wf) -> Any:
    return await dp.feed_update(bot, Update(update_id=next_id(), callback_query=query), **wf)


async def count_rows(engine: AsyncEngine, table) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(select(func.count()).select_from(table))).scalar() or 0
