from db.db_classes import User, Base, Photos
from sqlalchemy.orm import Session
from sqlalchemy import select

def init_test_data(engine, name: str, tg_id: str):
    squidward = User(name=name, fullname="Ivan Foobar", telegram_id = tg_id)
    with Session(engine) as session, session.begin():
        session.add(squidward)
    photo = Photos(hashsum="hash", likes=0)
    stmt = (
            select(User)
            .where(User.name == name)
            )
    with Session(engine) as session, session.begin():
        sq = session.scalars(stmt).one()
        photo.user_id = sq.id
        session.add(photo)

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
            print(photo)
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

def set_register_photo(engine, user_id: str, photo_id: str):
    pass

def unregister_photo(engine, user_id: str, photo_id: str):
    pass

def select_contest_photos(engine, user_id: str, photo_id: str):
    pass

def select_contest_winner(engine, user_id: str, photo_id: str):
    pass

def select_contest_theme(engine, user_id: str, photo_id: str):
    pass
