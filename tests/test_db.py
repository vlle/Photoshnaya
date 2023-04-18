import random

from sqlalchemy import create_engine, Engine
from db.db_operations import AdminDB, RegisterDB, ObjectFactory
from db.db_classes import Base, User
import pytest


class TGroup:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.group_id = group_id


class TUser:

    def __init__(self, name, i_id):
        self.name = name
        self.full_name = name + ' ' + name
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


@pytest.fixture
def user():
    return TUser(name="User №"
                      + str(random.randint(1, 10000)),
                 i_id=100 + random.randint(1, 2000))


@pytest.fixture
def registered_group(group, db):
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    register_unit = RegisterDB(db)
    register_unit.register_group(m_group)
    return register_unit


@pytest.fixture
def registered_user(registered_group, group, user, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = registered_group
    register_unit.register_user(m_user, m_group.telegram_id)
    return register_unit

@pytest.fixture()
def create_user(user, group, registered_group):
    user_list = []

    def create_user(*args, **kwargs) -> User:
        us = TUser(name="User №"
                      + str(random.randint(1, 10000)),
                 i_id=100 + random.randint(1, 2000))

        m_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        m_group = ObjectFactory.build_group(group.group_name, group.group_id)

        register_unit = registered_group
        register_unit.register_user(m_user, m_group.telegram_id)

        add_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        user_list.append(add_user)
        return add_user

    return create_user


def test_is_group_registered(registered_group, group):
    telegram_id = group.group_id
    register_unit = registered_group
    assert register_unit.find_group(telegram_id) is True


def test_is_group_not_registered(group, db):
    telegram_id = group.group_id
    register_unit = RegisterDB(db)
    assert register_unit.find_group(telegram_id) is False


def test_is_user_registered(registered_user, user, group, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = RegisterDB(db)
    assert register_unit.find_user_in_group(m_user.telegram_id, m_group.telegram_id) is True


def test_is_user_not_registered(registered_group, user, group, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = RegisterDB(db)
    assert register_unit.find_user_in_group(m_user.telegram_id, m_group.telegram_id) is False


def test_is_5_users_registered(create_user, group, db):
    users: list[User] = []
    for user in range(0, 5):
        users.append(create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        assert register_unit.find_user_in_group(user.telegram_id, m_group.telegram_id) is True


def test_is_5_users_not_registered(create_user, group, db):
    users: list[User] = []
    for user in range(0, 5):
        users.append(create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        assert register_unit.find_user_in_group(user.telegram_id, m_group.telegram_id + 110) is False


def test_is_admin_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(create_user())
    register_unit = RegisterDB(db)
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    m_user = ObjectFactory.build_user(users[0].name, users[0].name + ' Ivanov', users[0].telegram_id)
    register_unit.register_admin(m_user, m_group.telegram_id)

    m_user = ObjectFactory.build_user(users[0].name, users[0].name + ' Ivanov', users[0].telegram_id)
    
    assert AdminUnit.check_admin(m_user.telegram_id, m_group.telegram_id) is True


def test_is_admin_not_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(create_user())
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    m_user = ObjectFactory.build_user(users[0].name, users[0].name + ' Ivanov', users[0].telegram_id)
    
    assert AdminUnit.check_admin(m_user.telegram_id, m_group.telegram_id) is False


def test_is_photo_registered(create_user, group, db):
    users: list[User] = []
    for user in range(0, 5):
        users.append(create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        register_unit.register_photo_for_contest(user.telegram_id, m_group.telegram_id)
    all_photo_ids = register_unit.select_contest_photos_ids(m_group.telegram_id)
    assert len(all_photo_ids) == 5


def test_is_photo_registered_without_duplicating_submissions(create_user, group, db):
    users: list[User] = []
    for user in range(0, 5):
        users.append(create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        register_unit.register_photo_for_contest(user.telegram_id, m_group.telegram_id)
        register_unit.register_photo_for_contest(user.telegram_id, m_group.telegram_id)
    all_photo_ids = register_unit.select_contest_photos_ids(m_group.telegram_id)
    assert len(all_photo_ids) == 5


def test_is_vote_not_started(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    assert AdminUnit.get_current_vote_status(m_group.telegram_id) == False


def test_is_vote_started(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    AdminUnit.change_current_vote_status(m_group.telegram_id)

    assert AdminUnit.get_current_vote_status(m_group.telegram_id) == True

def test_is_vote_changed_again(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    cur_res = AdminUnit.get_current_vote_status(m_group.telegram_id)
    AdminUnit.change_current_vote_status(m_group.telegram_id)
    AdminUnit.change_current_vote_status(m_group.telegram_id)
    new_res = AdminUnit.get_current_vote_status(m_group.telegram_id)

    assert cur_res == new_res
