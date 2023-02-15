from sqlalchemy import exc
from sqlalchemy.sql.coercions import expect
from db.db_classes import User, Photo, Group, groupUser, groupPhoto
from sqlalchemy.orm import Session
from sqlalchemy import select


def set_like_photo(engine, photo_id: str):
    stmt = (
            select(Photo)
            .where(Photo.id == photo_id)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one() 
        photo.likes += 1
        likes = photo.likes
    return likes



def get_like_photo(engine, tg_id: str, hash = None) -> int:
    # in specific group? or what?
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    likes = 0
    with Session(engine) as session, session.begin():
        try:
            photos = session.scalars(stmt)
            for i in photos:
                print(i)
        except exc.NoResultFound:
            pass

    return likes


def set_register_photo(engine, tg_id: str, grtg_id: str,
                       user_p=None, group_p=None):
    stmt_sel = (
            select(User)
            .where(User.telegram_id == tg_id)
            )
    stmtG_sel = (
            select(Group)
            .where(Group.telegram_id == grtg_id)
            )
    with Session(engine) as session, session.begin():
        try:
            user = session.scalars(stmt_sel).one()
            group = session.scalars(stmtG_sel).one()
        except exc.NoResultFound:
            if (user_p):
                register_user(engine, user_p, grtg_id, group_p)
            if (group_p):
                register_group(engine, group_p)

        user = session.scalars(stmt_sel).one()
        group = session.scalars(stmtG_sel).one()
        photo = Photo(likes=0, user_id=user.id)
        user.photos.append(photo)
        group.photos.append(photo)
        session.add(photo)


def get_register_photo(engine, tg_id: str) -> int:
    id = -1
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    with Session(engine) as session, session.begin():
        try:
            photo = session.scalars(stmt).one()
            id = photo.id
        except exc.NoResultFound:
            pass

    return id


def unregister_photo(engine, user_id: str, photo_id: str):
    pass


def select_contest_photos(engine, group_id: str) -> list:
    ret = []
    stmtG = (
            select(Photo)
            .join(
                groupPhoto,
                  (Photo.id == groupPhoto.c.photo_id) 
                  )
            .where(groupPhoto.c.group_id == (
                select(Group.id).where(Group.telegram_id == group_id).scalar_subquery()))
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for photo in photos:
            print(photo)
            print("Printer")
            ret.append(photo)
    return ret


def set_contest_winner(engine, user_id: str, photo_id: str):
    pass


def get_contest_winner(engine, user_id: str, photo_id: str):
    pass


def set_contest_theme(engine, user_id: str, photo_id: str):
    pass


def get_contest_theme(engine, user_id: str, photo_id: str):
    pass

def build_group(name: str, telegram_id: str, contest_theme: str) -> Group:
    groupFrog = Group(name=name, telegram_id=telegram_id, contest_theme=contest_theme)
    return groupFrog

def build_user(name: str, full_name: str, user_id: str) -> User:
    human = User(name=name, full_name=full_name, telegram_id=user_id)
    return human

def find_group(engine, telegram_id: str) -> bool:
    stmt = (
            select(Group)
            .where(Group.telegram_id == telegram_id)
            )
    search_result = True
    with Session(engine) as session, session.begin():
        try:
            search = session.scalars(stmt).one()
            search_result = search is not None
        except exc.NoResultFound:
            search_result = False

    return search_result


def find_user(engine, telegram_id: str) -> bool:
    stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            )
    search_result = None
    with Session(engine) as session, session.begin():
        try:
            search = session.scalars(stmt).one()
            search_result = search is not None
        except exc.NoResultFound:
            search_result = False

    return search_result

def find_user_in_group(engine, telegram_user_id, group_telegram_id) -> list:
    stmt = (
            select(User)
            .join(
                groupUser,
                (User.id == groupUser.c.user_id) 
                )
            .where(groupUser.c.group_id == (
                select(Group.id).where(Group.telegram_id == group_telegram_id).scalar_subquery()))
            .where(groupUser.c.user_id == (select(User.id).where(User.telegram_id == telegram_user_id).scalar_subquery()))
            )
    ret = []
    with Session(engine) as session, session.begin():
        search_result = session.scalars(stmt)
        print(search_result)
        for i in search_result: 
            ret.append(i)

    return ret


def register_group(engine, group: Group) -> str:
    if (find_group(engine, group.telegram_id) is True):
        return "Группа уже зарегистрирована. 😮"

    with Session(engine) as session, session.begin():
        session.add(group)

    return "Зарегистрировал группу. "


def register_user(engine, user: User, tg_group_id: str, group=None)\
        -> str:
    if (find_user(engine, user.telegram_id)) is True:
        # check user in group
        return "User was already registered"

    stmt = select(Group).where(Group.telegram_id == tg_group_id)
    with Session(engine) as session, session.begin():
        try:
            search_result = session.scalars(stmt).one()
        except exc.NoResultFound:
            register_group(engine, group)

        search_result = session.scalars(stmt).one()
        user.groups.append(search_result)
        session.add(user)

    return "User was added"

def register_user_and_group(engine, group: Group, user: User, group_telegram_id: str) -> str:
    message = "None yet"
    register_group(engine, group)
    register_user(engine, user, group_telegram_id)
    return message

def init_test_data(engine, name: str, usertg_id: str, tggroup_id: str):
    group = build_group(name, tggroup_id, "None")
    user = build_user(name, name+" Foobar", usertg_id)  
    register_user_and_group(engine, group, user, tggroup_id)

    set_register_photo(engine, usertg_id, tggroup_id)
