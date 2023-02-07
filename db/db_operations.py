from sqlalchemy import exc
from sqlalchemy.sql.coercions import expect
from db.db_classes import User, Photo, Group, groupUser, groupPhoto
from sqlalchemy.orm import Session
from sqlalchemy import select

def set_like_photo_hash(engine, tg_id: str, hash: str):
    stmt = (
            select(Photo)
            .join(Photo.id)
            .where(User.telegram_id == tg_id)
            .where(Photo.hash == hash)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one() 
        try:
            photo.likes += 1
            likes = photo.likes
            session.add(photo)
        except:
            pass
    return likes

def set_like_photo_single(engine, id: str) -> int:
    stmt = (
            select(Photo)
            .where(Photo.id == id)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        try:
            photo = session.scalars(stmt).one() 
            photo.likes += 1
            likes = photo.likes
            session.add(photo)
        except exc.NoResultFound:
            print("Error, no result found")
            pass
        except exc.ArgumentError:
            print("Error, no set available found")
            pass
    return likes


def set_like_photo(engine, tg_id: str, hash = None):
    likes = -1
    if (hash is not None):
        likes = set_like_photo_hash(engine, tg_id, hash)
    else:
        likes = set_like_photo_single(engine, tg_id)
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
            user = session.scalars(stmt).one() 
            likes = user.likes
        except exc.NoResultFound:
            pass

    return likes

def get_like_photo_hash(engine, tg_id: str, hash: str) -> int:
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            .where(Photo.hash == hash)
            )
    likes = 0
    with Session(engine) as session, session.begin():
        try:
            user = session.scalars(stmt).one() 
            likes = user.likes
        except exc.NoResultFound:
            pass

    return likes

def get_like_photo(engine, tg_id: str, hash = None) -> int:
    likes = -1
    if (hash is not None):
        likes = get_like_photo_hash(engine, tg_id, hash)
    else:
        likes = get_like_photo_single(engine, tg_id)
    return likes

def set_register_photo(engine, tg_id: str):
    stmt_sel = (
            select(User)
            .where(User.telegram_id == tg_id)
            )
    with Session(engine) as session, session.begin():
        user = session.scalars(stmt_sel).one() 
        try:

            photo = Photo(hash="hash", likes=0, tg_link="ss", user_id = user.id)
            session.add(photo)
        except:
            pass

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
            select(Group)
            .where(Group.telegram_id == group_id)
            )
    with Session(engine) as session, session.begin():
        try:
            group = session.scalars(stmtG).one()
            print(group)
            stmt = (
                    select(groupPhoto)
                    .where(groupPhoto.group_id == group.id)
                    )
            result = session.execute(stmt)
            for i in result.scalars():
                print(f"RES = {i}")
                ret.append(i)
        except:
            pass
    return ret

def set_contest_winner(engine, user_id: str, photo_id: str):
    pass

def get_contest_winner(engine, user_id: str, photo_id: str):
    pass

def set_contest_theme(engine, user_id: str, photo_id: str):
    pass

def get_contest_theme(engine, user_id: str, photo_id: str):
    pass


def init_test_data(engine, name: str, usertg_id: str, tggroup_id: str):
    human = User(name=name, full_name= name + "Foobar", telegram_id = usertg_id)
    group = Group(name="Жабы", telegram_id = tggroup_id, contest_theme = "#пляжи")
    stmt = (
            select(User)
            .where(User.telegram_id == usertg_id)
            )
    stmtG = (
            select(Group)
            .where(Group.telegram_id == tggroup_id)
            )
    with Session(engine) as session, session.begin():
        session.add(human)
        session.add(group)

    with Session(engine) as session, session.begin():
        gr = session.scalars(stmtG).one()
        hu = session.scalars(stmt).one()
        human_group = groupUser(user_id = hu.id, group_id = gr.id)
        session.add(human_group)
        print(human_group)

    set_register_photo(engine, usertg_id)
