import random

from sqlalchemy import create_engine, Engine
from db.db_operations import Register, ObjectFactory
from db.db_classes import Base
import pytest


class TGroup:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.group_id = group_id


class TUser:

    def __init__(self, name, i_id):
        self.name = name
        self.fullname = name + ' ' + name
        self.id = i_id


@pytest.fixture
def db():
    engine: Engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def group():
    return TGroup(group_name="FriendsGroupNumber"
                             + str(random.randint(1, 100)),
                  group_id=100)


def user():
    return TUser(name="User №"
                      + str(random.randint(1, 100)),
                 i_id=100 + random.randint(1, 200))


@pytest.fixture
def registered_group(group, db):
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    register_unit = Register(db)
    register_unit.register_group(m_group)
    return register_unit


@pytest.fixture
def registered_user(registered_group, group, user, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = registered_group
    register_unit.register_user(m_user, m_group.telegram_id, m_group)
    return m_user, m_group


def test_is_group_registered(registered_group, group):
    telegram_id = group.group_id
    register_unit = registered_group
    assert register_unit.find_group(telegram_id) is True


def test_is_group_not_registered(group, db):
    telegram_id = group.group_id
    register_unit = Register(db)
    assert register_unit.find_group(telegram_id) is False


def test_is_user_registered(group, db):
    telegram_id = group.group_id
    register_unit = Register(db)
    assert register_unit.find_group(telegram_id) is False
