from sqlalchemy.engine.base import ExceptionContextImpl
from sqlalchemy.sql.coercions import expect
from db.db_classes import User, Base, Photo
from sqlalchemy.orm import Session
from sqlalchemy import select

def set_like_photo_hash(engine, tg_id: str, hash = None):
    pass
    #stmt = (
    #        select(Photo)
    #        .join(User, Photo.user_id = User.id)
    #        .where(User.telegram_id == tg_id)
    #        )
    #likes = -1
    #with Session(engine) as session, session.begin():
    #    photo = session.scalars(stmt).one() 
    #    try:
    #        photo.likes += 1
    #        likes = photo.likes
    #        session.add(photo)
    #    except:
    #        pass
    #return likes

def set_like_photo_single(engine, tg_id: str, hash = None) -> int:
    stmt = (
            select(Photo)
            .join(User.id)
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
        user = session.scalars(stmt).one() 
        try:
            likes = user.likes
        except:
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
        user = session.scalars(stmt).one() 
        try:
            likes = user.likes
        except:
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
            if (user.id is None):
                raise Exception("Oh")

            photo = Photo(hash="hash", likes=0, group_membership="none", tg_link="ss", user_id = user.id)
            session.add(photo)
        except:
            pass

def get_register_photo(engine, tg_id: str) -> str:
    link = "0"
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    # with Session(engine) as session, session.begin():
    #     photo = session.scalars(stmt).one()
    #     try:
    #         link = photo.tg_link
    #     except:
    #         pass

    return link


def unregister_photo(engine, user_id: str, photo_id: str):
    pass

def select_contest_photos(engine, user_id: str, photo_id: str):
    pass

def select_contest_winner(engine, user_id: str, photo_id: str):
    pass

def select_contest_theme(engine, user_id: str, photo_id: str):
    pass

def init_test_data(engine, name: str, tg_id: str):
    squidward = User(name=name, full_name= name + "Foobar", telegram_id = tg_id)
    with Session(engine) as session, session.begin():
        session.add(squidward)

    set_register_photo(engine, tg_id)
