from db_classes import Base
from sqlalchemy import MetaData, create_engine
import sys    
print("In module products sys.path[0], __package__ ==", sys.path[0], __package__)
# declarative base class
engine = create_engine("sqlite+pysqlite:///sqlite3.db", echo=True)
metadata_obj = MetaData()
Base.metadata.create_all(engine)

#session = Session(engine)

#with Session(engine) as session, session.begin():
#    session.add(krabs)

