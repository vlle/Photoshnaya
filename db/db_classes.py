from typing import List
from typing import Optional
from sqlalchemy.orm import Mapped
from sqlalchemy import Integer, String, ForeignKey, MetaData, create_engine
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
    telegram_nick: Mapped[str]

    photo: Mapped[List["Address"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r}),\
                telegram_id={self.telegram_id!r}, telegram_nick={self.telegram_nick}"

class Photos(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    hashsum: Mapped[str]
    user_id = mapped_column(ForeignKey("user_account.id"))

    user: Mapped[User] = relationship(back_populates="photos")

    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, hashsum={self.hashsum!r})"

