from sqlalchemy.engine.base import ExceptionContextImpl
from sqlalchemy.sql.coercions import expect
from db.db_classes import User, Base, Photos
from sqlalchemy.orm import Session
from sqlalchemy import select


def set_like_photo(engine, user_id: str, tg_id: str):
    stmt = (
            select(Photos)
            #.join(Photos.user_id)
            #.where(User.telegram_id == tg_id)
            #.where(Photos.user_id == user_id)
            )
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one() 
        try:
            photo.likes += 1
            session.add(photo)
        except:
            pass

def get_like_photo(engine, user_id: str, tg_id: str) -> int:
    stmt = (
            select(Photos)
            #.join(User)
            #.where(User.telegram_id == tg_id)
            #.where(Photos.user_id == user_id)
            )
    ans = 0
    with Session(engine) as session, session.begin():
        for row in session.execute(stmt):
            print(row)
            ######ans = row["likes"]
    return 0

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

            photo = Photos(hashsum="hash", likes=0, tg_link="ss", user_id = user.id)
            session.add(photo)
        except:
            pass

def get_register_photo(engine, tg_id: str) -> str:
    link = "0"
    stmt = (
            select(Photos)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one()
        try:
            link = photo.tg_link
        except:
            pass

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
    squidward = User(name=name, fullname="Ivan Foobar", telegram_id = tg_id)
    with Session(engine) as session, session.begin():
        session.add(squidward)

    set_register_photo(engine, tg_id)
