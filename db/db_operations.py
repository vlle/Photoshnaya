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


def get_like_photo_single(engine, tg_id: str) -> int:
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


def get_like_photo(engine, tg_id: str, hash = None) -> int:
    likes = -1
    likes = get_like_photo_single(engine, tg_id)
    return likes


def set_register_photo(engine, tg_id: str, grtg_id: str):
    stmt_sel = (
            select(User)
            .where(User.telegram_id == tg_id)
            )
    stmtG_sel = (
            select(Group)
            .where(Group.telegram_id == grtg_id)
            )
    with Session(engine) as session, session.begin():
        user = session.scalars(stmt_sel).one() 
        group = session.scalars(stmtG_sel).one() 
        photo = Photo(likes=0, user_id = user.id)
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
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for photo in photos:
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


def register_user_and_group(engine, group: Group, user: User) -> str:
    message = "None yet"
    stmt = (
            select(User)
            .where(User.telegram_id == user.telegram_id)
            )
    stmtGroup = (
            select(Group)
            .where(Group.telegram_id == group.telegram_id)
            )
    with Session(engine) as session, session.begin():
        player = session.scalars(stmt)
        chat = session.scalars(stmtGroup)
        if player is None:
            if chat is None: # need to check if user registered in this group
                session.add(chat)
            human.groups.append(group)
            session.add(human)
            message = f"Зарегистрировал тебя, пользователь {name}"
        else:
            message = "Уже зарегистрированы."
    return message

def init_test_data(engine, name: str, usertg_id: str, tggroup_id: str):
    #human = User(name=name, full_name=name+"Foobar", telegram_id=usertg_id)
    human = build_user(name, name+" Foobar", usertg_id)
    groupFrog = Group(name="Жабы", telegram_id=tggroup_id, contest_theme="#пляжи")
    human.groups.append(groupFrog)
    with Session(engine) as session, session.begin():
        session.add(human)
        session.add(groupFrog)

    set_register_photo(engine, usertg_id, tggroup_id)
