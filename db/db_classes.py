from typing import List
from typing import Optional
from sqlalchemy.orm import Mapped
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column


# declarative base class
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[Optional[str]]
    telegram_id: Mapped[str]

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, full_name={self.full_name!r}),\
                telegram_id={self.telegram_id!r}"

class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str]
    likes: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"));

    # projects = relationship(
    #     "Project",
    #     secondary=Table(
    #         "employee_project",
    #         Base.metadata,
    #         Column("employee_id", Integer, ForeignKey("employee.id"), primary_key=True),
    #         Column("project_id", Integer, ForeignKey("project.id"), primary_key=True),
    #     ),
    #     backref="employees",
    # )

    def __repr__(self) -> str:
        return f"Photo(id={self.id!r}, hashsum={self.hash!r})"

class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    telegram_id: Mapped[str]
    contest_theme: Mapped[str]

    def __repr__(self) -> str:
        return f"Group(id={self.id!r}, name={self.name!r}, telegram_id={self.telegram_id!r}, contest_theme={self.contest_theme})"

class groupPhoto(Base):
    __tablename__ = "group_photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photo.id"));
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"));

    def __repr__(self) -> str:
        return f"GroupPhoto(id={self.id!r}, photo_id={self.photo_id!r}, group_id={self.group_id!r})"

class groupUser(Base):
    __tablename__ = "group_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"));
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"));

    def __repr__(self) -> str:
        return f"GroupUser(id={self.id!r}, user_id={self.user_id!r}, group_id={self.group_id!r})"

