import os
import random
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from db.db_operations import RegisterDB, ObjectFactory
from db.db_classes import Base
import pytest

from handlers.internal_logic.on_join import i_on_user_join
from utils.TelegramUserClass import TelegramChat, TelegramUser


@pytest.fixture
async def db():
    load_dotenv()
    ps_url = os.environ.get("testps_url")
    if not ps_url:
        return
    engine: AsyncEngine = create_async_engine(ps_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest.fixture
async def random_user():
    user_name = "John " + str(random.randint(0, 10000))
    user_full_name = user_name + user_name
    user_id = random.randint(-10000, 10000)
    return user_name, user_full_name, user_id


@pytest.fixture
async def random_group():
    group_name = "PhotoGroup " + str(random.randint(0, 10000))
    group_id = random.randint(10000, 210000)
    return group_name, group_id


@pytest.fixture
async def registered_group(random_group, db):
    group_name, group_id = random_group
    m_group = ObjectFactory.build_group(group_name, group_id)

    register_unit = RegisterDB(db)
    await register_unit.register_group(m_group)
    return group_name, group_id


@pytest.fixture
async def registered_user(registered_group, random_user, db):
    user_name, user_full_name, user_id = random_user
    group_name, group_id = registered_group

    m_user = ObjectFactory.build_user(user_name, user_full_name, user_id)
    m_group = ObjectFactory.build_group(group_name, group_id)

    register_unit = registered_group
    await register_unit.register_user(m_user, m_group.telegram_id)
    return register_unit


async def test_is_on_join_registers_admin(random_user, random_group, db):
    user_name, user_full_name, user_id = random_user
    group_name, group_id = random_group
    user = TelegramUser(user_name, user_full_name, user_id, group_id, 1)
    chat = TelegramChat(group_name, group_name + group_name, group_id, 1, "group")

    register_unit = RegisterDB(db)
    msg, reg_msg = await i_on_user_join(
        register_unit=register_unit, user=user, chat=chat
    )

    assert (isinstance(msg, str) and isinstance(reg_msg, str)) is True
    assert await register_unit.find_group(group_id) is True
    assert msg.startswith("Добавил в качестве админа") is True
    assert reg_msg.startswith("Зарегистрировал группу.") is True
