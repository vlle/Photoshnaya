from __future__ import annotations
from typing import List
from typing import Optional
from sqlalchemy.orm import Mapped
from sqlalchemy import String, ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


# declarative base class
class Base(DeclarativeBase):
    pass


groupPhoto = Table(
    "groupPhoto",
    Base.metadata,
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

groupUser = Table(
    "groupUser",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

photoLike = Table(
    "photoLike",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
)

groupAdmin = Table(
    "groupAdmin",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[Optional[str]]
    telegram_id: Mapped[int]
    photos: Mapped[List["Photo"]] = relationship()
    groups: Mapped[List["Group"]] = relationship(
        secondary=groupUser, back_populates="users"
    )
    admin_in: Mapped[List["Group"]] = relationship(
        secondary=groupAdmin, back_populates="admins"
    )
    liked: Mapped[List["Photo"]] = relationship(
        secondary=photoLike, back_populates="likes"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, full_name=\
                {self.full_name!r}),\
                telegram_id={self.telegram_id!r}"


class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    likes: Mapped[List["User"]] = relationship(
        secondary=photoLike, back_populates="photos"
    )
    groups: Mapped[List["Group"]] = relationship(
        secondary=groupPhoto, back_populates="photos"
    )

    def __repr__(self) -> str:
        return f"Photo(id={self.id!r}), likes=({self.likes!r}), user_id = \
                {self.user_id!r}, file_id = {self.file_id!r})"


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    telegram_id: Mapped[int]
    contest_theme: Mapped[str]
    contest_duration_sec: Mapped[int]
    users: Mapped[List["User"]] = relationship(
        secondary=groupUser, back_populates="groups"
    )
    photos: Mapped[List["Photo"]] = relationship(
        secondary=groupPhoto, back_populates="groups"
    )
    admins: Mapped[List["User"]] = relationship(
        secondary=groupAdmin, back_populates="admin_in"
    )

    def __repr__(self) -> str:
        return f"Group(id={self.id!r}, name={self.name!r}, telegram_\
                id={self.telegram_id!r}, contest_theme={self.contest_theme})"

class TemporaryPhotoLike(Base):
    __tablename__ = "tmpPhotoLike"

    id: Mapped[int] = mapped_column(primary_key=True)
    likes_t: Mapped[int]
    liked_t: Mapped[int]
