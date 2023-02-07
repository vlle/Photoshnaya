from typing import List
from typing import Optional
from sqlalchemy.orm import Mapped
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


# declarative base class
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[Optional[str]]

    telegram_id: Mapped[str]
    # group_membership: Mapped[Optional[List[str]]]

    photo: Mapped[Optional[List["Photo"]]] = relationship()

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, full_name={self.full_name!r}),\
                telegram_id={self.telegram_id!r}"

class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str]
    likes: Mapped[int]

    telegram_id: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"));

    def __repr__(self) -> str:
        return f"Photo(id={self.id!r}, hashsum={self.hash!r})"

# class Photos(Base):


# class Group(Base):
#     __tablename__ = "group"
# 
#     id: Mapped[int] = mapped_column(primary_key=True)
#     name: Mapped[str] = mapped_column(String(30))
# 
#     telegram_id: Mapped[str]
#     telegram_nick: Mapped[Optional[str]]
#     # group_membership: Mapped[Optional[List[str]]]
# 
# 
#     def __repr__(self) -> str:
#         return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r}),\
#                 telegram_id={self.telegram_id!r}, telegram_nick={self.telegram_nick}"
