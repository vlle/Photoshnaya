from db.db_classes import Base
from sqlalchemy import create_engine
from db.db_operations import init_test_data

engine = create_engine("sqlite+pysqlite:///sqlite3.db", echo=True)
Base.metadata.create_all(engine)

init_test_data(engine, "Ivan", "213", "214")


