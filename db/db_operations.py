from typing import Any

from sqlalchemy import exc
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_session, async_sessionmaker

from db.db_classes import tmp_photo_like, User, Photo, Group,\
        group_user, group_photo, group_admin, Contest, \
        photo_like, contest_user
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from sqlalchemy import Engine

from sqlalchemy.sql import func


class ObjectFactory:

    def __init__(self) -> None:
        pass

    @staticmethod
    def build_group(name: str, telegram_id: int) -> Group:
        group = Group(name=name, telegram_id=telegram_id)
        return group

    @staticmethod
    def build_contest(contest_name: str, contest_duration_sec: int) -> Contest:
        contest = Contest(contest_name=contest_name,
                          contest_duration_sec=contest_duration_sec)
        return contest

    @staticmethod
    def build_user(name: str, full_name: str, user_id: int) -> User:
        human = User(name=name, full_name=full_name, telegram_id=user_id)
        return human

    @staticmethod
    def build_theme(user_theme: list[str]) -> str:
        if user_theme[1][0] != '#':
            theme = '#' + user_theme[1]
        else:
            theme = '#'
            for let in user_theme[1]:
                if let == '#':
                    continue
                theme += let

        return theme


class BaseDB:

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        async_session: async_sessionmaker[AsyncSession]

    def get_contest_id(self, telegram_group_id: int) -> int:
        stmt = (
                select(Contest)
                .join(Group, Group.id == Contest.group_id)
                .where(Group.telegram_id == telegram_group_id)
                .order_by(Contest.id.desc())
                )
        with Session(self.engine) as session, session.begin():
            contest = session.scalars(stmt).first()
            if not contest:
                return -1
            return contest.id

    def get_user_id(self, telegram_user_id: int) -> int:
        with Session(self.engine) as session, session.begin():
            ret_id = session.scalars(
                    select(User.id)
                    .where(User.telegram_id == telegram_user_id)
                    ).one()
            return ret_id


class SelectDB(BaseDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    def select_file_type(self, id: int) -> str:
        stmt = (
                select(Photo)
                .where(Photo.id == id)
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).one()
            res = res.telegram_type
        return res

    def select_file_id(self, id: int) -> str:
        stmt = (
                select(Photo)
                .where(Photo.id == id)
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).one()
            return res.file_id

    def select_file_type_by_file_id(self, id: str) -> str:
        stmt = (
                select(Photo)
                .where(Photo.file_id == id)
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).one()
            res = res.telegram_type
        return res

    def find_group(self, telegram_id: int) -> bool:
        stmt = (
                select(Group)
                .where(Group.telegram_id == telegram_id)
                )
        with Session(self.engine) as session, session.begin():
            search = session.scalars(stmt).first()
            return search is not None

    def find_user_in_group(self, telegram_user_id: int,
                           group_telegram_id: int) -> bool:
        stmt = (
                select(User)
                .join(
                    group_user,
                    (User.id == group_user.c.user_id)
                    )
                .where(group_user.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_telegram_id)
                    .scalar_subquery()))
                .where(group_user.c.user_id.in_(
                    select(User.id)
                    .where(User.telegram_id == telegram_user_id)
                    .scalar_subquery()))
                )
        with Session(self.engine) as session, session.begin():
            try:
                search_result = session.scalars(stmt).one()
                ret = search_result is not None
            except exc.NoResultFound:
                ret = False
            except exc.MultipleResultsFound:
                ret = True

        return ret

    def select_next_contest_photo(self, group_id: int,
                                  current_photo: int) -> list[str]:
        ret: list[Any] = []
        stmt_g = (
                select(Photo)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .where(
                    (group_photo.c.group_id == (
                        select(Group.id)
                        .where(Group.telegram_id == group_id)
                        .scalar_subquery())
                     ) &
                    (Photo.id > current_photo))
                .order_by(Photo.id)
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmt_g).first()
            if photos:
                ret.append(photos.file_id)
                ret.append(photos.id)
        return ret

    def select_prev_contest_photo(self, group_id: int,
                                  current_photo: int) -> list[str]:
        ret = []
        stmt_g = (
                select(Photo)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .where(
                    (group_photo.c.group_id == (
                        select(Group.id)
                        .where(Group.telegram_id == group_id)
                        .scalar_subquery())
                     ) &
                    (Photo.id < current_photo))
                .order_by(Photo.id.desc())
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmt_g).first()
            if photos:
                ret.append(photos.file_id)
                ret.append(photos.id)
        return ret

    def select_contest_photos_ids(self, group_id: int) -> list:
        ret = []
        stmt_g = (
                select(Photo)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .where(group_photo.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_id).scalar_subquery()))
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmt_g)
            for photo in photos:
                ret.append(photo.file_id)
        return ret

    def select_contest_photos_primary_ids(self, group_id: int) -> list:
        ret = []
        stmt_g = (
                select(Photo)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .where(group_photo.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_id).scalar_subquery()))
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmt_g)
            for photo in photos:
                ret.append(photo.id)
        return ret

    def select_contest_photos_ids_and_types(self, group_id: int) -> list:
        ret = []
        stmt_g = (
                select(Photo)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .where(group_photo.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_id).scalar_subquery()))
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmt_g)
            for photo in photos:
                ret.append([photo.file_id, photo.telegram_type])
        return ret

    def get_current_vote_status(self, group_id: int) -> bool:
        ret: bool = False
        stmt = (
                select(Group)
                .where(Group.telegram_id == group_id)
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).first()
            if res:
                if res.vote_in_progress == 0:
                    ret = False
                else:
                    ret = True

        return ret


class LikeDB(SelectDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    def like_photo(self, tg_id: int, p_id: int) -> int:
        search_stmt_user = select(User).where(User.telegram_id == tg_id)
        search_stmt_photo = select(Photo).where(Photo.id == p_id)
        likes = 0
        with Session(self.engine) as session, session.begin():
            user = session.scalars(search_stmt_user).one()
            photo = session.scalars(search_stmt_photo).one()
            stmt = insert(tmp_photo_like).values(user_id=user.id,
                                                 photo_id=photo.id)
            session.execute(stmt)

        return likes

    def like_photo_with_file_id(self, tg_id: int, p_id: int) -> int:
        search_stmt_user = select(User).where(User.telegram_id == tg_id)
        search_stmt_photo = select(Photo).where(Photo.file_id == p_id)
        likes = 0
        with Session(self.engine) as session, session.begin():
            user = session.scalars(search_stmt_user).one()
            photo = session.scalars(search_stmt_photo).one()
            stmt = insert(tmp_photo_like).values(user_id=user.id,
                                                 photo_id=photo.id)
            session.execute(stmt)

        return likes

    def remove_like_photo(self, tg_id: int, photo_id: int) -> None:
        stmt = (
                delete(tmp_photo_like)
                .where(tmp_photo_like.c.user_id ==
                       (select(User.id)
                        .where(User.telegram_id == tg_id)
                        .scalar_subquery())
                       & (tmp_photo_like.c.photo_id == photo_id)
                       ))
        with Session(self.engine) as session, session.begin():
            session.execute(stmt)

    def is_photo_liked(self, tg_id: int, ph_id: str) -> int:
        stmt = (
                select(tmp_photo_like)
                .join(User, tmp_photo_like.c.user_id == User.id)
                .join(Photo, tmp_photo_like.c.photo_id == Photo.id)
                .where(User.telegram_id == tg_id)
                .where(Photo.id == ph_id)
                )
        likes = 0
        with Session(self.engine) as session, session.begin():
            like = session.scalars(stmt).fetchall()
            for _ in like:
                likes += 1

        return likes

    def get_all_likes_for_user(self, u_telegram_id: int, g_telegram_id: int):
        ret: list = []
        stmt = (
                select(tmp_photo_like)
                .join(Photo)
                .join(group_photo)
                .join(Group)
                .where((Group.telegram_id == g_telegram_id)
                       & (User.telegram_id == u_telegram_id))
                )
        with Session(self.engine) as session, session.begin():
            for row in session.execute(stmt):
                ret.append(row)
        return ret

    def delete_likes_from_tmp_vote(self, u_telegram_id: int,
                                   g_telegram_id: int):
        ret: list = []
        stmt = (
                delete(tmp_photo_like)
                .where(tmp_photo_like.c.photo_id.in_(
                    select(Photo.id)
                    .join(group_photo)
                    .join(Group)
                    .where((Group.telegram_id == g_telegram_id)
                           & (User.telegram_id == u_telegram_id))
                    ))
                )
        with Session(self.engine) as session, session.begin():
            session.execute(stmt)
        return ret

    def insert_all_likes(self, u_telegram_id: int, g_telegram_id: int):
        select_stmt = (
                select(tmp_photo_like)
                .join(User, User.id == tmp_photo_like.c.user_id)
                .join(group_photo, tmp_photo_like.c.photo_id ==
                      group_photo.c.photo_id)
                .join(Photo, Photo.id == tmp_photo_like.c.photo_id)
                .join(Group, Group.id == group_photo.c.group_id)
                .where((Group.telegram_id == g_telegram_id)
                       & (User.telegram_id == u_telegram_id))
                )
        stmt = insert(photo_like).from_select(["user_id", "photo_id"],
                                              select_stmt)
        with Session(self.engine) as session, session.begin():
            session.execute(stmt)


class VoteDB(LikeDB):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    def mark_user_voted(self, telegram_group_id: int, telegram_user_id: int):
        contest_id = self.get_contest_id(telegram_group_id)
        user_id = self.get_user_id(telegram_user_id)
        with Session(self.engine) as session, session.begin():
            stmt = insert(contest_user).values(contest_id=contest_id,
                                               user_id=user_id)
            session.execute(stmt)

    def is_user_not_allowed_to_vote(self, telegram_group_id: int,
                                    telegram_user_id: int) -> bool:
        contest_id = self.get_contest_id(telegram_group_id)
        user_id = self.get_user_id(telegram_user_id)
        stmt = (
                select(contest_user)
                .where((contest_user.c.user_id == user_id)
                       & (contest_user.c.contest_id == contest_id))
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt)
            allow = 0
            for _ in res:
                allow += 1
            return allow > 0

    def erase_all_photos(self, telegram_group_id: int):
        stmt_id = (
                select(Group)
                .where(Group.telegram_id == telegram_group_id)
                )
        with Session(self.engine) as session, session.begin():
            group = session.scalars(stmt_id).one()
            stmt_del = (
                    delete(group_photo)
                    .where(group_photo.c.group_id == group.id)
                    )
            session.execute(stmt_del)
        return

    def select_winner_from_contest(self, telegram_group_id: int):
        stmt = (
                select(photo_like.c.photo_id,
                       func.count(photo_like.c.photo_id))
                .join(group_photo, photo_like.c.photo_id ==
                      group_photo.c.photo_id)
                .join(Group, group_photo.c.group_id == Group.id)
                .where(Group.telegram_id == telegram_group_id)
                .group_by(photo_like.c.photo_id)
                .order_by(func.count(photo_like.c.photo_id).desc())
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).first()
            stmt_user = session.scalars(
                    select(User)
                    .join(Photo)
                    .where(Photo.id == res)
                    ).one()
            user = [stmt_user.name, stmt_user.full_name, stmt_user.telegram_id]
            if not res:
                return -1, None
            return res, user

    def select_all_likes(self, telegram_group_id: int, id: str):
        stmt = (
                select(
                       func.count(photo_like.c.photo_id))
                .join(group_photo, photo_like.c.photo_id ==
                      group_photo.c.photo_id)
                .join(Group, group_photo.c.group_id == Group.id)
                .join(Photo, group_photo.c.photo_id == Photo.id)
                .where(Group.telegram_id == telegram_group_id)
                .where(Photo.id == id)
                .group_by(photo_like.c.photo_id)
                .order_by(func.count(photo_like.c.photo_id).desc())
                )
        with Session(self.engine) as session, session.begin():
            rs = session.scalars(stmt).first()
        return rs

    def select_all_likes_file_id(self, telegram_group_id: int, file_id: str):
        stmt = (
                select(
                       func.count(photo_like.c.photo_id))
                .join(group_photo, photo_like.c.photo_id ==
                      group_photo.c.photo_id)
                .join(Group, group_photo.c.group_id == Group.id)
                .join(Photo, group_photo.c.photo_id == Photo.id)
                .where(Group.telegram_id == telegram_group_id)
                .where(Photo.file_id == file_id)
                .group_by(photo_like.c.photo_id)
                .order_by(func.count(photo_like.c.photo_id).desc())
                )
        with Session(self.engine) as session, session.begin():
            rs = session.scalars(stmt).first()
            if rs is None:
                return 0
        return rs

    def select_all_likes_with_user(self, telegram_group_id: int, file_id: str):
        stmt_like = (
                select(
                       func.count(photo_like.c.photo_id))
                .join(group_photo, photo_like.c.photo_id ==
                      group_photo.c.photo_id)
                .join(Group, group_photo.c.group_id == Group.id)
                .join(Photo, group_photo.c.photo_id == Photo.id)
                .where(Group.telegram_id == telegram_group_id)
                .where(Photo.file_id == file_id)
                .group_by(photo_like.c.photo_id)
                .order_by(func.count(photo_like.c.photo_id).desc())
                )
        stmt_user = (
                select(User)
                .join(Photo)
                .where(Photo.file_id == file_id)
                )
        with Session(self.engine) as session, session.begin():
            rs = session.scalars(stmt_like).first()
            rs_user: User = session.scalars(stmt_user).one()
            user_data = [rs_user.name, rs_user.full_name, rs_user.telegram_id]
        return rs, user_data


class RegisterDB(SelectDB):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    async def register_group(self, group: Group) -> tuple:
        #if self.find_group(group.telegram_id is True):
        #    return "Группа уже зарегистрирована. 😮", False
        contest = ObjectFactory.build_contest('-1', -1)
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                group.contest = contest
                session.add(group)

        return "Зарегистрировал группу. ", True

    def register_user(self, user: User, tg_group_id: int) -> str:
        if (self.find_user_in_group(user.telegram_id, tg_group_id)) is True:
            return "User was already registered"

        stmt = select(Group).where(Group.telegram_id == tg_group_id)
        with Session(self.engine) as session, session.begin():
            search_result = session.scalars(stmt).one()
            user.groups.append(search_result)
            session.add(user)

        return "User was added"

    async def register_admin(self, adm_user: User, group_id: int, group=None):
        stmt = select(Group).where(Group.telegram_id == group_id)
        stmt_user = select(User).where(User.telegram_id ==
                                       adm_user.telegram_id)
        with Session(self.engine) as session, session.begin():
            try:
                search_result = session.scalars(stmt).one()
                user_search = session.scalars(stmt_user).one_or_none()
            except exc.NoResultFound:
                if group:
                    self.register_group(group)
                search_result = session.scalars(stmt).one()
                user_search = session.scalars(stmt_user).one_or_none()
            if not user_search:
                adm_user.admin_in.append(search_result)
                adm_user.groups.append(search_result)
                session.add(adm_user)
            else:
                user_search.admin_in.append(search_result)
                user_search.groups.append(search_result)

        return "Добавил администратора."

    def register_photo_for_contest(self, user_tg_id: int, grtg_id: int,
                                   file_get_id='-1',
                                   user_p=None, group_p=None, type='photo') -> bool:
        stmt_sel = (
                select(User)
                .where(User.telegram_id == user_tg_id)
                )
        stmtg_sel = (
                select(Group)
                .where(Group.telegram_id == grtg_id)
                )
        stmt_photo_sel = (
                select(Photo)
                .join(group_photo)
                .join(User)
                .where(User.telegram_id == user_tg_id)
                )
        with Session(self.engine) as session, session.begin():
            try:
                user = session.scalars(stmt_sel).one()
                group = session.scalars(stmtg_sel).one()
            except exc.NoResultFound:
                if user_p:
                    self.register_user(user_p, grtg_id)
                if group_p:
                    self.register_group(group_p)
                user = session.scalars(stmt_sel).one()
                group = session.scalars(stmtg_sel).one()

            possible_register = session.scalars(stmt_photo_sel).first()
            if possible_register:
                return False

            photo = Photo(file_id=file_get_id,
                          user_id=user.id, telegram_type=type)

            user.photos.append(photo)
            group.photos.append(photo)
            session.add(photo)
        return True

    async def get_contest_theme(self, group_id: int):
        stmt = (
                select(Contest)
                .join(Group, Group.id == Contest.group_id)
                .where(Group.telegram_id == group_id)
                .order_by(Contest.id.desc())
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    result = await session.execute(stmt)
                    theme = result.scalars().one()
                    if theme:
                        theme = theme.contest_name
                    else:
                        theme = None
                except exc.NoResultFound:
                    theme = "Ошибка, не нашел группу."
        return theme


class AdminDB(RegisterDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    def change_current_vote_status(self, group_id: int) -> bool:
        ret: bool = False
        stmt = (
                select(Group)
                .where(Group.telegram_id == group_id)
                )
        with Session(self.engine) as session, session.begin():
            res = session.scalars(stmt).first()
            print(res)
            if res:
                if not res.vote_in_progress:
                    ret = res.vote_in_progress = True
                else:
                    ret = res.vote_in_progress = False

        return ret

    def select_all_administrated_groups(self, telegram_user_id: int) -> list:
        ret: list = []
        stmt = (
                select(Group)
                .join(group_admin)
                .join(User)
                .where(User.telegram_id == telegram_user_id)
                )
        with Session(self.engine) as session, session.begin():
            ids = session.scalars(stmt)
            for id in ids:
                ret.append([id.name, id.telegram_id])

        return ret

    async def check_admin(self, user_id: int, group_id: int) -> bool:
        async with async_session() as session:
            admin_right = False
            stmt = (
                    select(User)
                    .join(group_admin,
                          (User.id == group_admin.c.user_id)
                          )
                    .where(group_admin.c.group_id == (
                        select(Group.id).where(Group.telegram_id == group_id)
                        ).scalar_subquery()))
            with Session(self.engine) as session, session.begin():
                try:
                    admin = session.scalars(stmt).one()
                    if user_id == admin.telegram_id:
                        admin_right = True
                except exc.NoResultFound:
                    pass
                except exc.MultipleResultsFound:
                    admin_right = True

            return admin_right

    def set_contest_theme(self, group_id: int, theme: str,
                          contest_duration_sec=604800) -> str:
        stmt_g = (
                select(Group.id).where(Group.telegram_id == group_id)
                )
        obj_factory = ObjectFactory()
        theme_object = obj_factory.build_contest(theme, contest_duration_sec)
        with Session(self.engine) as session, session.begin():
            group_id = session.scalars(stmt_g).one()
            theme_object.group_id = group_id
            session.add(theme_object)

        return f'Тема зарегистрирована. {theme}'
