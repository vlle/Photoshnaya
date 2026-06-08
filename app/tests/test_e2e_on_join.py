"""E2E вступления бота в группу (on_user_join, my_chat_member).

Когда бота добавляют в группу, он должен зарегистрировать группу и сделать
добавившего админом — иначе никто не сможет управлять челленджами.
"""
from __future__ import annotations

from db.db_classes import Group, group_admin
from db.db_operations import AdminDB

from tests.conftest import count_rows, feed_chat_member, make_chat_member_updated

GID = 313131
ADDER = 414


async def test_on_join_registers_group_and_admin(dispatcher, bot, engine, workflow_kwargs):
    await feed_chat_member(
        dispatcher,
        bot,
        make_chat_member_updated(actor_id=ADDER, chat_id=GID, chat_title="Photo Club"),
        **workflow_kwargs,
    )

    assert await count_rows(engine, Group) == 1, "группа должна зарегистрироваться"
    assert await AdminDB(engine).check_admin(ADDER, GID) is True, "добавивший должен стать админом"
    assert await count_rows(engine, group_admin) == 1
    assert bot.sent("SendMessage"), "бот должен отчитаться в чат о регистрации"


async def test_on_join_twice_is_idempotent(dispatcher, bot, engine, workflow_kwargs):
    event = make_chat_member_updated(actor_id=ADDER, chat_id=GID, chat_title="Photo Club")
    await feed_chat_member(dispatcher, bot, event, **workflow_kwargs)
    await feed_chat_member(
        dispatcher,
        bot,
        make_chat_member_updated(actor_id=ADDER, chat_id=GID, chat_title="Photo Club"),
        **workflow_kwargs,
    )

    assert await count_rows(engine, Group) == 1, "повторное добавление не должно плодить группы"
    assert await count_rows(engine, group_admin) == 1, "права админа тоже должны остаться идемпотентными"
