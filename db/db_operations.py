from db.db_classes import User, Base, Photos
from sqlalchemy.orm import Session
from sqlalchemy import select

def init_test_data(engine, user_id: int):
    squidward = User(name="Ivan", fullname="Ivan Foobar", telegram_id=user_id)
    photo = Photos(hashsum="hash", likes=0, user_id=user_id)
    with Session(engine) as session, session.begin():
        session.add(squidward)
        session.add(photo)

def set_like_photo(engine, user_id: str):
    stmt = (
            select(Photos)
            .join(User)
            .where(User.telegram_id == user_id)
            #.where(Photos.user_id == user_id)
            )
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one() 
        photo.likes += 1

def get_like_photo(engine, user_id: str, photo_id: str) -> int:
    stmt = (
            select(Photos)
            .join(User)
            .where(User.telegram_id == user_id)
            #.where(Photos.user_id == user_id)
            )
    ans = 0
    with Session(engine) as session, session.begin():
        for row in session.execute(stmt.first()):
            print(row)
            ans = row[0]
    return ans

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
