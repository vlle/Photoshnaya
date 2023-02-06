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
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    telegram_id: Mapped[str]
    telegram_nick: Mapped[Optional[str]]

    photo: Mapped[Optional[List["Photos"]]] = relationship()

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r}),\
                telegram_id={self.telegram_id!r}, telegram_nick={self.telegram_nick}"

class Photos(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    hashsum: Mapped[str]
    likes: Mapped[int]
    tg_link: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"));

    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, hashsum={self.hashsum!r})"

