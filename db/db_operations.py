from db.db_classes import User, Base, Photos
#from .init_db import engine
from sqlalchemy.orm import Session

def init_test_data(engine):
    session = Session(engine)
    squidward = User(name="Ivan", fullname="Ivan Foobar", telegram_id="1919118841")
    with Session(engine) as session, session.begin():
        session.add(squidward)

def like_photo(engine, user_id: str, photo_id: str):
    pass

def remove_like_photo(engine, user_id: str, photo_id: str):
    pass

def register_photo(engine, user_id: str, photo_id: str):
    pass

def unregister_photo(engine, user_id: str, photo_id: str):
    pass

def select_contest_photos(engine, user_id: str, photo_id: str):
    pass

def select_contest_winner(engine, user_id: str, photo_id: str):
    pass

def select_contest_theme(engine, user_id: str, photo_id: str):
    pass
