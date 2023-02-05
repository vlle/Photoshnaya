from db_classes import Base
from sqlalchemy import MetaData, create_engine
from db_operations import init_test_data

# declarative base class
engine = create_engine("sqlite+pysqlite:///sqlite3.db", echo=True)
metadata_obj = MetaData()
Base.metadata.create_all(engine)

#init_test_data(engine)

