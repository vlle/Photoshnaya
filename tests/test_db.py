import os
import random
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from db.db_operations import AdminDB, RegisterDB, ObjectFactory, LikeDB, VoteDB
from db.db_classes import Base, User
import pytest


class TGroup:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.group_id = group_id


class TUser:
    def __init__(self, name, i_id):
        self.name = name
        self.full_name = name + " " + "Ivanov"
        self.id = i_id


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
def group():
    return TGroup(
        group_name="FriendsGroupNumber" + str(random.randint(1, 1000)), group_id=100
    )


@pytest.fixture
def group_another():
    return TGroup(
        group_name="FriendsGroupNumber" + str(random.randint(1, 1000)), group_id=200
    )


@pytest.fixture
def user():
    return TUser(
        name="User №" + str(random.randint(-100, 10000)),
        i_id=100 + random.randint(1, 2000),
    )


@pytest.fixture
async def registered_group(group, db):
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    register_unit = RegisterDB(db)
    await register_unit.register_group(m_group)
    return register_unit


@pytest.fixture
async def registered_user(registered_group, group, user, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = registered_group
    await register_unit.register_user(m_user, m_group.telegram_id)
    return register_unit


@pytest.fixture()
async def create_user(user, group, registered_group):
    async def c_u(*args, **kwargs):
        us = TUser(
            name="User №" + str(random.randint(1, 10000)),
            i_id=100 + random.randint(1, 2000),
        )

        m_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        m_group = ObjectFactory.build_group(group.group_name, group.group_id)

        register_unit = registered_group
        await register_unit.register_user(m_user, m_group.telegram_id)

        add_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        return add_user

    yield c_u


@pytest.fixture
async def registered_group_another(group_another, db):
    m_group = ObjectFactory.build_group(
        group_another.group_name, group_another.group_id
    )
    register_unit = RegisterDB(db)
    await register_unit.register_group(m_group)
    return register_unit


@pytest.fixture()
async def create_user_another(user, group_another, registered_group_another):
    async def c_u(*args, **kwargs):
        us = TUser(
            name="User №" + str(random.randint(1, 10000)),
            i_id=100 + random.randint(1, 2000),
        )

        m_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        m_group = ObjectFactory.build_group(
            group_another.group_name, group_another.group_id
        )

        register_unit = registered_group_another
        await register_unit.register_user(m_user, m_group.telegram_id)

        add_user = ObjectFactory.build_user(us.name, us.full_name, us.id)
        return add_user

    yield c_u


async def test_is_get_theme(registered_group, group):
    telegram_id = group.group_id
    register_unit = registered_group
    assert await register_unit.get_contest_theme(telegram_id) == "-1"


async def test_is_false_get_theme(registered_group, group):
    telegram_id = group.group_id
    register_unit = registered_group
    assert await register_unit.get_contest_theme(telegram_id) != "-2"


async def test_is_group_registered(registered_group, group):
    telegram_id = group.group_id
    register_unit = registered_group
    assert await register_unit.find_group(telegram_id) is True


async def test_is_group_not_registered(group, db):
    telegram_id = group.group_id
    register_unit = RegisterDB(db)
    assert await register_unit.find_group(telegram_id) is False


async def test_is_user_registered(registered_user, user, group, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = RegisterDB(db)
    assert (
        await register_unit.find_user_in_group(m_user.telegram_id, m_group.telegram_id)
        is True
    )


async def test_is_user_not_registered(registered_group, user, group, db):
    m_user = ObjectFactory.build_user(user.name, user.full_name, user.id)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    register_unit = RegisterDB(db)
    assert (
        await register_unit.find_user_in_group(m_user.telegram_id, m_group.telegram_id)
        is False
    )


async def test_is_5_users_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        assert (
            await register_unit.find_user_in_group(
                user.telegram_id, m_group.telegram_id
            )
            is True
        )


async def test_is_5_users_not_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1])
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        assert (
            await register_unit.find_user_in_group(
                user.telegram_id, m_group.telegram_id + 123123
            )
            is False
        )


async def test_is_admin_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = RegisterDB(db)
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    m_user = ObjectFactory.build_user(
        users[0].name, users[0].name + " Ivanov", users[0].telegram_id
    )
    await register_unit.register_admin(m_user, m_group.telegram_id)

    m_user = ObjectFactory.build_user(
        users[0].name, users[0].name + " Ivanov", users[0].telegram_id
    )

    assert await AdminUnit.check_admin(m_user.telegram_id, m_group.telegram_id) is True


async def test_is_admin_not_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    m_user = ObjectFactory.build_user(
        users[0].name, users[0].name + " Ivanov", users[0].telegram_id
    )

    assert await AdminUnit.check_admin(m_user.telegram_id, m_group.telegram_id) is False


async def test_is_photo_registered(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    assert len(all_photo_ids) == 5


async def test_is_photo_registered_count(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 3):
        users.append(await create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    assert len(all_photo_ids) == 3
    assert len(all_photo_ids) == 3


async def test_is_photo_registered_without_duplicating_submissions(
    create_user, group, db
):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = RegisterDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id
        )
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    assert len(all_photo_ids) == 5


async def test_is_vote_not_started(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    assert await AdminUnit.get_current_vote_status(m_group.telegram_id) is False


async def test_is_vote_started(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    await AdminUnit.change_current_vote_status(m_group.telegram_id)

    assert await AdminUnit.get_current_vote_status(m_group.telegram_id) is True


async def test_is_vote_changed_again(create_user, group, db):
    AdminUnit = AdminDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)
    cur_res = await AdminUnit.get_current_vote_status(m_group.telegram_id)
    await AdminUnit.change_current_vote_status(m_group.telegram_id)
    await AdminUnit.change_current_vote_status(m_group.telegram_id)
    new_res = await AdminUnit.get_current_vote_status(m_group.telegram_id)

    assert cur_res == new_res


async def test_is_vote_finished_correctly(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[2].telegram_id, all_photo_ids[0])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)

    photo_winner, user = await vote.select_winner_from_contest(m_group.telegram_id)
    assert photo_winner == 1


async def test_is_vote_finished_correctly_second(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[2].telegram_id, all_photo_ids[2])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)

    photo_winner, user = await vote.select_winner_from_contest(m_group.telegram_id)
    assert photo_winner == 3


async def test_is_vote_finished_correctly_multiple_winners(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[1])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)

    photo_winner, user = await vote.select_winner_from_contest(m_group.telegram_id)
    await vote.erase_all_photos(m_group.telegram_id)
    assert user is not None
    assert user[-1] is False
    assert photo_winner in [1, 2]


async def test_is_likes_correctly_counted(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[2].telegram_id, all_photo_ids[2])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)
    all_photo_ids = await register_unit.select_contest_photos_primary_ids(
        m_group.telegram_id
    )

    list_of_likes = [1, 1, 3, 0, 0]
    i = 0
    for id in all_photo_ids:
        photo_like = await vote.select_all_likes(m_group.telegram_id, id)
        if photo_like is None:
            photo_like = 0
        assert photo_like == list_of_likes[i]
        i += 1


async def test_is_likes_correctly_counted_file_id(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[2].telegram_id, all_photo_ids[2])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)

    list_of_likes = [1, 1, 3, 0, 0]
    i = 0
    for id in all_photo_ids:
        photo_like = await vote.select_all_likes_file_id(m_group.telegram_id, id)
        if photo_like is None:
            photo_like = 0
        assert photo_like == list_of_likes[i]
        i += 1


async def test_is_likes_correctly_counted_with_user(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[0])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[1])
    await like.like_photo_with_file_id(users[0].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[1].telegram_id, all_photo_ids[2])
    await like.like_photo_with_file_id(users[2].telegram_id, all_photo_ids[2])
    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)

    list_of_likes = [1, 1, 3, 0, 0]
    i = 0
    for id in all_photo_ids:
        photo_like, user = await vote.select_all_likes_with_user(
            m_group.telegram_id, id
        )
        if photo_like is None:
            photo_like = 0
        assert photo_like == list_of_likes[i]
        assert user[0] == users[i].name
        assert user[1] == users[i].full_name
        assert user[2] == users[i].telegram_id
        i += 1


async def test_is_photos_deleted_correctly(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = AdminDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    first_val = len(all_photo_ids)
    await vote.erase_all_photos(m_group.telegram_id)
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group.telegram_id)
    second_val = len(all_photo_ids)
    assert first_val == 5
    assert first_val != second_val
    assert second_val == 0


# test multi-admin
# test multi-user
async def test_is_multi_user_ok():
    pass


# test delete with multiple groups
async def test_is_multi_groups_ok(
    create_user, create_user_another, group, group_another, db
):
    users1: list[User] = []
    for _ in range(0, 5):
        users1.append(await create_user())

    users2: list[User] = []
    for _ in range(0, 5):
        users2.append(await create_user_another())

    register_unit = AdminDB(db)
    vote = VoteDB(db)
    m_group1 = ObjectFactory.build_group(group.group_name, group.group_id)
    m_group2 = ObjectFactory.build_group(
        group_another.group_name, group_another.group_id
    )
    print(m_group1)
    print(m_group2)

    for user in users1:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group1.telegram_id, file_get_id=str(file_id)
        )

    for user in users2:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group2.telegram_id, file_get_id=str(file_id)
        )

    all_photo_ids = await register_unit.select_contest_photos_ids(m_group1.telegram_id)
    first_val = len(all_photo_ids)
    await vote.erase_all_photos(m_group1.telegram_id)
    all_photo_ids = await register_unit.select_contest_photos_ids(m_group1.telegram_id)
    second_val = len(all_photo_ids)
    assert first_val == 5
    assert first_val != second_val
    assert second_val == 0

    all_photo_ids_second = await register_unit.select_contest_photos_ids(
        m_group2.telegram_id
    )

    second_group_val = len(all_photo_ids_second)
    await vote.erase_all_photos(m_group2.telegram_id)
    all_photo_ids_second = await register_unit.select_contest_photos_ids(
        m_group2.telegram_id
    )
    second_group_val2 = len(all_photo_ids_second)

    assert second_group_val == 5
    assert second_group_val != second_group_val2
    assert second_group_val2 == 0


async def test_is_multi_admins_ok(
    create_user, create_user_another, group, group_another, db
):
    users1: list[User] = []
    for _ in range(0, 5):
        users1.append(await create_user())

    users2: list[User] = []
    users2.append(users1[0])
    users2.append(users1[1])
    for _ in range(2, 5):
        users2.append(await create_user_another())

    register_unit = RegisterDB(db)
    AdminUnit = AdminDB(db)
    m_group1 = ObjectFactory.build_group(group.group_name, group.group_id)
    m_group2 = ObjectFactory.build_group(
        group_another.group_name, group_another.group_id
    )
    user_in1_admin_in2 = ObjectFactory.build_user(
        users1[0].name, users1[0].name + " Ivanov", users1[0].telegram_id
    )
    user_in2_admin_in1 = ObjectFactory.build_user(
        users1[1].name, users1[1].name + " Ivanov", users1[1].telegram_id
    )
    await register_unit.register_admin(user_in1_admin_in2, m_group2.telegram_id)
    await register_unit.register_admin(user_in2_admin_in1, m_group1.telegram_id)
    administrated_groups1: list = await AdminUnit.select_all_administrated_groups(
        user_in1_admin_in2.telegram_id
    )
    administrated_groups2: list = await AdminUnit.select_all_administrated_groups(
        user_in2_admin_in1.telegram_id
    )

    assert len(administrated_groups1) == len(administrated_groups2)
    assert administrated_groups2 != administrated_groups1

    await register_unit.register_admin(user_in2_admin_in1, m_group2.telegram_id)

    administrated_groups1: list = await AdminUnit.select_all_administrated_groups(
        user_in1_admin_in2.telegram_id
    )
    administrated_groups2: list = await AdminUnit.select_all_administrated_groups(
        user_in2_admin_in1.telegram_id
    )

    assert len(administrated_groups1) != len(administrated_groups2)
    assert administrated_groups1[0] in administrated_groups2


async def test_select_prev_contest_photo(create_user, group, db):
    users: list[User] = []
    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    vote = VoteDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_primary_ids(
        m_group.telegram_id
    )
    print(all_photo_ids)
    first_id = all_photo_ids[4]
    _, next_id = await like.select_prev_contest_photo(m_group.telegram_id, first_id)
    assert next_id == all_photo_ids[3]
    _, next_id = await like.select_prev_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[2]
    _, next_id = await like.select_prev_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[1]
    _, next_id = await like.select_prev_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[0]


async def test_select_next_contest_photo(create_user, group, db):
    users: list[User] = []

    for _ in range(0, 5):
        users.append(await create_user())
        print(users[-1].telegram_id)
    register_unit = AdminDB(db)
    like = LikeDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_primary_ids(
        m_group.telegram_id
    )
    first_id = all_photo_ids[0]
    _, next_id = await like.select_next_contest_photo(m_group.telegram_id, first_id)
    assert next_id == all_photo_ids[1]
    _, next_id = await like.select_next_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[2]
    _, next_id = await like.select_next_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[3]
    _, next_id = await like.select_next_contest_photo(m_group.telegram_id, int(next_id))
    assert next_id == all_photo_ids[4]


async def test_is_contests_counted_correctly(create_user, group, db):
    pass


async def test_is_vote_async_correct(create_user, group, db):
    users: list[User] = []

    for _ in range(0, 5):
        users.append(await create_user())
    register_unit = AdminDB(db)
    like = LikeDB(db)
    m_group = ObjectFactory.build_group(group.group_name, group.group_id)

    for user in users:
        file_id = random.randint(0, 100000)
        await register_unit.register_photo_for_contest(
            user.telegram_id, m_group.telegram_id, file_get_id=str(file_id)
        )
    all_photo_ids = await register_unit.select_contest_photos_primary_ids(
        m_group.telegram_id
    )

    id1 = await like.select_file_id(all_photo_ids[0])
    id2 = await like.select_file_id(all_photo_ids[1])
    id3 = await like.select_file_id(all_photo_ids[2])

    await like.like_photo_with_file_id(users[0].telegram_id, id1)
    await like.like_photo_with_file_id(users[0].telegram_id, id2)
    await like.like_photo_with_file_id(users[0].telegram_id, id3)

    await like.like_photo_with_file_id(users[1].telegram_id, id1)
    await like.like_photo_with_file_id(users[1].telegram_id, id2)
    await like.like_photo_with_file_id(users[1].telegram_id, id3)

    await like.like_photo_with_file_id(users[2].telegram_id, id1)

    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[0]) > 0
    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[1]) > 0
    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[2]) > 0

    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[0]) > 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[1]) > 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[2]) > 0

    await like.insert_all_likes(users[0].telegram_id, m_group.telegram_id)
    await like.delete_likes_from_tmp_vote(users[0].telegram_id, m_group.telegram_id)
    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[0]) == 0
    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[1]) == 0
    assert await like.is_photo_liked(users[0].telegram_id, all_photo_ids[2]) == 0

    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[0]) > 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[1]) > 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[2]) > 0

    await like.insert_all_likes(users[1].telegram_id, m_group.telegram_id)
    await like.delete_likes_from_tmp_vote(users[1].telegram_id, m_group.telegram_id)
    await like.insert_all_likes(users[2].telegram_id, m_group.telegram_id)
    await like.delete_likes_from_tmp_vote(users[2].telegram_id, m_group.telegram_id)
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[0]) == 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[1]) == 0
    assert await like.is_photo_liked(users[1].telegram_id, all_photo_ids[2]) == 0

    v = VoteDB(db)
    t, s = await v.select_winner_from_contest(m_group.telegram_id)
    assert t == all_photo_ids[0]
