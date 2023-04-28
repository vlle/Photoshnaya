from __future__ import annotations
from typing import List
from typing import Optional
import datetime
from sqlalchemy.orm import Mapped
from sqlalchemy import BigInteger, Boolean, String, ForeignKey, Table, Column, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sqlalchemy.sql import functions


# declarative base class

# create votecontest Table
# create groupcontest Table
# create contest Table

class Base(DeclarativeBase):
    pass


group_photo = Table(
    "group_photo",
    Base.metadata,
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

group_user = Table(
    "group_user",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

group_admin = Table(
    "group_admin",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

photo_like = Table(
    "photo_like",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
)

tmp_photo_like = Table(
    "tmp_photo_like",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
)


contest_user = Table(
    "contest_user",
    Base.metadata,
    Column("contest_id", ForeignKey("contest.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[Optional[str]]
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    photos: Mapped[List["Photo"]] = relationship()
    created_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=functions.now()
    )
    groups: Mapped[List["Group"]] = relationship(
        secondary=group_user, back_populates="users"
    )
    admin_in: Mapped[List["Group"]] = relationship(
        secondary=group_admin, back_populates="admins"
    )
    liked: Mapped[List["Photo"]] = relationship(
        secondary=photo_like, back_populates="likes"
    )
    voted_in: Mapped[List["Contest"]] = relationship(
        secondary=contest_user, back_populates="have_vote_from"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, full_name=\
                {self.full_name!r}),\
                telegram_id={self.telegram_id!r}"


class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str]
    telegram_type: Mapped[str] = mapped_column(String(15), default="photo")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    likes: Mapped[List["User"]] = relationship(
        secondary=photo_like, back_populates="photos"
    )
    groups: Mapped[List["Group"]] = relationship(
        secondary=group_photo, back_populates="photos"
    )

    def __repr__(self) -> str:
        return f"Photo(id={self.id!r}), likes=({self.likes!r}), user_id = \
                {self.user_id!r}, file_id = {self.file_id!r})"


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    telegram_id: Mapped[int] = mapped_column(BigInteger)

    contest: Mapped["Contest"] = relationship(back_populates="group")
    vote_in_progress: Mapped[int] = mapped_column(Boolean, default=False)

    created_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=functions.now()
    )
    users: Mapped[List["User"]] = relationship(
        secondary=group_user, back_populates="groups"
    )
    photos: Mapped[List["Photo"]] = relationship(
        secondary=group_photo, back_populates="groups"
    )
    admins: Mapped[List["User"]] = relationship(
        secondary=group_admin, back_populates="admin_in"
    )

    def __repr__(self) -> str:
        return f"Group(id={self.id!r}, name={self.name!r}, telegram_\
                id={self.telegram_id!r}), vote_status={self.vote_in_progress}"


class Contest(Base):
    __tablename__ = "contest"

    id: Mapped[int] = mapped_column(primary_key=True)
    contest_name: Mapped[str]
    contest_duration_sec: Mapped[int]
    link_to_results: Mapped[Optional[str]]

    created_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=functions.now()
    )
    have_vote_from: Mapped[List["User"]] = relationship(
        secondary=contest_user, back_populates="voted_in"
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"))
    group: Mapped["Group"] = relationship(back_populates="contest")

    def __repr__(self) -> str:
        return f"Contest(id={self.id!r}), name=({self.contest_name!r})"
