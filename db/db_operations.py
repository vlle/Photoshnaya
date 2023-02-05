from db.db_classes import User, Base, Photos
#from .init_db import engine
from sqlalchemy.orm import Session

def init_test_data(engine):
    session = Session(engine)
    squidward = User(name="Ivan", fullname="Ivan Foobar", telegram_id="1919118841")
    with Session(engine) as session, session.begin():
        session.add(squidward)
