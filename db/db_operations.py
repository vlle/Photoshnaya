from typing import Any

from sqlalchemy import exc
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from db.db_classes import tmp_photo_like, User, Photo, Group,\
        group_user, group_photo, group_admin, Contest, \
        photo_like, contest_user
from sqlalchemy.orm import selectinload
from sqlalchemy import select, delete

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
    def build_vote_link(bot_username: str, group_id: int | str):
        bot_link = f"t.me/{bot_username}?start=" + str(group_id) + "_3"
        return bot_link

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

    @staticmethod
    def build_theme_fsm(user_theme: str) -> str:
        if user_theme[0] != '#':
            theme = '#' + user_theme
        else:
            theme = '#'
            for let in user_theme:
                if let == '#':
                    continue
                theme += let

        return theme

class BaseDB:

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def get_contest_id(self, telegram_group_id: int) -> int:
        stmt = (
                select(Contest)
                .join(Group, Group.id == Contest.group_id)
                .where(Group.telegram_id == telegram_group_id)
                .order_by(Contest.id.desc())
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                contest = (await session.scalars(stmt)).first()
                if not contest:
                    return -1
                return contest.id

    async def get_user_id(self, telegram_user_id: int) -> int:
        stmt = (
                select(User.id)
                .where(User.telegram_id == telegram_user_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                ret_id = (await session.scalars(stmt)).one_or_none()
                if ret_id is None:
                    ret_id = -1
                return ret_id


class SelectDB(BaseDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

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
                    theme = result.scalars().first()
                    if theme:
                        theme = theme.contest_name
                    else:
                        theme = None
                except exc.NoResultFound:
                    theme = "Ошибка, не нашел группу."
        return theme

    async def select_file_type(self, id: int) -> str:
        stmt = (
                select(Photo)
                .where(Photo.id == id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).one()
                res = res.telegram_type
        return res

    async def select_file_id(self, id: int) -> str:
        stmt = (
                select(Photo)
                .where(Photo.id == id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).one()
                return res.file_id

    async def select_file_type_by_file_id(self, id: str) -> str:
        stmt = (
                select(Photo)
                .where(Photo.file_id == id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).one()
                res = res.telegram_type
        return res

    async def find_photo_by_user_in_group(self, u_telegram_id: int,
                                          g_telegram_id: int):
        stmt = (
                select(Photo)
                .join(User)
                .join(
                    group_photo,
                    (Photo.id == group_photo.c.photo_id)
                    )
                .join(Group)
                .where(User.telegram_id == u_telegram_id)
                .where(Group.telegram_id == g_telegram_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).one_or_none()
                if res is None:
                    return None
                return [res.id, res.file_id, res.telegram_type]


    async def find_group(self, telegram_id: int) -> bool:
        stmt = (
                select(Group)
                .where(Group.telegram_id == telegram_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                search = await session.scalars(stmt)
                return search.one_or_none() is not None

    async def find_user_in_group(self, telegram_user_id: int,
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                search_result = await session.scalars(stmt)
                return search_result.first() is not None


    async def select_next_contest_photo(self, group_id: int,
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photos = (await session.scalars(stmt_g)).first()
                if photos:
                    ret.append(photos.file_id)
                    ret.append(photos.id)
        return ret

    async def select_prev_contest_photo(self, group_id: int,
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photos = (await session.scalars(stmt_g)).first()
                if photos:
                    ret.append(photos.file_id)
                    ret.append(photos.id)
        return ret

    async def select_contest_photos_ids(self, group_id: int) -> list:
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photos = await session.scalars(stmt_g)
                for photo in photos:
                    ret.append(photo.file_id)
        return ret

    async def select_contest_photos_primary_ids(self, group_id: int) -> list:
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photos = await session.scalars(stmt_g)
                for photo in photos:
                    ret.append(photo.id)
        return ret

    async def select_contest_photos_ids_and_types(self, group_id: int) -> list:
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photos = await session.scalars(stmt_g)
                for photo in photos:
                    ret.append([photo.file_id, photo.telegram_type])
        return ret

    async def get_current_vote_status(self, group_id: int) -> bool:
        ret: bool = False
        stmt = (
                select(Group)
                .where(Group.telegram_id == group_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                srch = await session.scalars(stmt)
                res = srch.one()
                print(res)
                if res.vote_in_progress == 0:
                    ret = False
                elif res:
                    ret = True

        return ret


class LikeDB(SelectDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    async def like_photo(self, tg_id: int, p_id: int) -> int:
        search_stmt_user = select(User).where(User.telegram_id == tg_id)
        search_stmt_photo = select(Photo).where(Photo.id == p_id)
        likes = 0
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                user = (await session.scalars(search_stmt_user)).one()
                photo = (await session.scalars(search_stmt_photo)).one()
                stmt = insert(tmp_photo_like).values(user_id=user.id,
                                                     photo_id=photo.id)
                await session.execute(stmt)

        return likes

    async def like_photo_with_file_id(self, tg_id: int, p_id: int) -> int:
        search_stmt_user = select(User).where(User.telegram_id == tg_id)
        search_stmt_photo = select(Photo).where(Photo.file_id == p_id)
        likes = 0
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                user_srch = await session.scalars(search_stmt_user)
                photo_srch = await session.scalars(search_stmt_photo)
                user = user_srch.one()
                photo = photo_srch.one()
                stmt = insert(tmp_photo_like).values(user_id=user.id,
                                                     photo_id=photo.id)
                await session.execute(stmt)

        return likes

    async def remove_like_photo(self, tg_id: int, photo_id: int) -> None:
        stmt = (
                delete(tmp_photo_like)
                .where(tmp_photo_like.c.user_id ==
                       (select(User.id)
                        .where(User.telegram_id == tg_id)
                        .scalar_subquery())
                       & (tmp_photo_like.c.photo_id == photo_id)
                       ))
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await session.execute(stmt)

    async def is_photo_liked(self, tg_id: int, ph_id: str) -> int:
        stmt = (
                select(tmp_photo_like)
                .join(User, tmp_photo_like.c.user_id == User.id)
                .join(Photo, tmp_photo_like.c.photo_id == Photo.id)
                .where(User.telegram_id == tg_id)
                .where(Photo.id == ph_id)
                )
        likes = 0
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                like = (await session.scalars(stmt)).fetchall()
                for _ in like:
                    likes += 1

        return likes

    async def get_all_likes_for_user(self, u_telegram_id: int, g_telegram_id: int):
        ret: list = []
        stmt = (
                select(tmp_photo_like)
                .join(Photo)
                .join(group_photo)
                .join(Group)
                .where((Group.telegram_id == g_telegram_id)
                       & (User.telegram_id == u_telegram_id))
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = await session.execute(stmt)
                for row in res:
                    ret.append(row)
        return ret

    async def delete_likes_from_tmp_vote(self, u_telegram_id: int,
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await session.execute(stmt)
        return ret

    async def insert_all_likes(self, u_telegram_id: int, g_telegram_id: int):
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await session.execute(stmt)


class VoteDB(LikeDB):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    async def mark_user_voted(self, telegram_group_id: int, telegram_user_id: int):
        contest_id = await self.get_contest_id(telegram_group_id)
        user_id = await self.get_user_id(telegram_user_id)
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = insert(contest_user).values(contest_id=contest_id,
                                                   user_id=user_id)
                await session.execute(stmt)

    async def is_user_not_allowed_to_vote(self, telegram_group_id: int,
                                    telegram_user_id: int) -> bool:
        contest_id = await self.get_contest_id(telegram_group_id)
        user_id = await self.get_user_id(telegram_user_id)
        if (user_id == -1):
            return False
        stmt = (
                select(contest_user)
                .where((contest_user.c.user_id == user_id)
                       & (contest_user.c.contest_id == contest_id))
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).one_or_none()
                return res is not None

    async def erase_all_photos(self, telegram_group_id: int):
        stmt_id = (
                select(Group)
                .where(Group.telegram_id == telegram_group_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                group = (await session.scalars(stmt_id)).one()
                stmt_del = (
                        delete(group_photo)
                        .where(group_photo.c.group_id == group.id)
                        )
                await session.execute(stmt_del)
        return

    async def select_winner_from_contest(self, telegram_group_id: int):
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                res = (await session.scalars(stmt)).first()
                if not res:
                    return -1, None
                stmt_user = await session.scalars(
                        select(User)
                        .join(Photo)
                        .where(Photo.id == res)
                        )
                stmt_user = stmt_user.one()
                user = [stmt_user.name, stmt_user.full_name, stmt_user.telegram_id]
                return res, user

    async def select_all_likes(self, telegram_group_id: int, id: str):
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                rs = await session.scalars(stmt)
                return rs.first()

    async def select_all_likes_file_id(self, telegram_group_id: int, file_id: str):
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                rs = await session.scalars(stmt)
                rs = rs.first()
                if rs is None:
                    return 0
        return rs

    async def select_all_likes_with_user(self, telegram_group_id: int, file_id: str):
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                rs = (await session.scalars(stmt_like)).first()
                rs_user: User = (await session.scalars(stmt_user)).one()
                user_data = [rs_user.name, rs_user.full_name, rs_user.telegram_id]
        return rs, user_data


class RegisterDB(SelectDB):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)

    async def register_group(self, group: Group) -> tuple:
        #why no test ffs
        if await self.find_group(group.telegram_id) is True:
            return "Группа уже зарегистрирована. 😮", False
        contest = ObjectFactory.build_contest('-1', -1)
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                group.contest = contest
                session.add(group)

        return "Зарегистрировал группу. ", True

    #async def register_user(self, user: User, tg_group_id: int) -> str:
    #    if (await self.find_user_in_group(user.telegram_id, tg_group_id)) is True:
    #        return "User was already registered"
    #    stmt = select(Group).where(Group.telegram_id == tg_group_id)
    #    async with AsyncSession(self.engine) as session:
    #        async with session.begin():
    #            rs = (await session.scalars(select(User)
    #                                         .where(User.telegram_id
    #                                                == user.telegram_id))).one_or_none()
    #            if rs is not None:
    #                user = rs
    #                search_result = await session.scalars(stmt)
    #                group = search_result.one()
    #                user.groups.append(group)
    #            else:
    #                search_result = await session.scalars(stmt)
    #                group = search_result.one()
    #                user.groups.append(group)
    #                session.add(user)

    #    return "User was added"


    async def register_user(self, user: User, tg_group_id: int) -> str:
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                # Check if the user already exists in the database
                rs = (await session.scalars(select(User)
                                            .options(selectinload(User.groups))
                                            .where(User.telegram_id 
                                                   == user.telegram_id))).one_or_none()
                if rs is not None:
                    # User already exists, add the group to their groups list
                    group = (await session.scalars(select(Group)
                                                   .where(Group.telegram_id
                                                   == tg_group_id))).one()
                    if group not in rs.groups:
                        rs.groups.append(group)
                    return "User was already registered"

                # User doesn't exist, add them to the database
                group = (await session.scalars(
                        select(Group).
                        where(Group.telegram_id == tg_group_id))).one()
                user.groups.append(group)
                session.add(user)
                try:
                    await session.commit()
                    return "User was added"
                except exc.IntegrityError as e:
                    await session.rollback()
                    # Duplicate user detected, return an appropriate error message
                    if "UNIQUE constraint failed" in str(e):
                        return "User was already registered"
                    else:
                        return "Failed to register user"


    async def register_admin(self, adm_user: User, group_id: int):
        stmt = select(Group).where(Group.telegram_id == group_id)
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                rs = (await session.scalars(select(User)
                                            .options(selectinload(User.groups))
                                            .options(selectinload(User.admin_in))
                                            .where(User.telegram_id 
                                                   == adm_user.telegram_id)
                                            )).one_or_none()
                search_result = await session.scalars(stmt)
                grp = search_result.one()
                if rs is None:
                    adm_user = await session.merge(adm_user)
                    adm_user.groups.append(grp)
                    adm_user.admin_in.append(grp)
                else:
                    rs.groups.append(grp)
                    rs.admin_in.append(grp)

        return "Добавил администратора."

    async def register_photo_for_contest(self, user_tg_id: int, grtg_id: int,
                                         file_get_id='-1',
                                         user_p=None, group_p=None,
                                         type='photo') -> bool:
        stmt_sel = (
                select(User)
                .options(selectinload(User.photos))
                .where(User.telegram_id == user_tg_id)
                )
        stmtg_sel = (
                select(Group)
                .options(selectinload(Group.photos))
                .where(Group.telegram_id == grtg_id)
                )
        stmt_photo_sel = (
                select(Photo)
                .join(group_photo)
                .join(User)
                .where(User.telegram_id == user_tg_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                u_search = await session.scalars(stmt_sel)
                g_search = await session.scalars(stmtg_sel)
                user = u_search.one_or_none()
                group = g_search.one_or_none()
                if not user and user_p:
                    await self.register_user(user_p, grtg_id)
                    u_search = await session.scalars(stmt_sel)
                    user = u_search.one()
                if not group and group_p:
                    await self.register_group(group_p)
                    g_search = await session.scalars(stmtg_sel)
                    group = g_search.one()

                #possible_register = await session.scalars(stmt_photo_sel)
                #if possible_register.one_or_none() is not None:
                #    return False


                if user and group:
                    photo = Photo(file_id=file_get_id,
                                  user_id=user.id, telegram_type=type)
                    user.photos.append(photo)
                    group.photos.append(photo)
                    session.add(photo)
        return True



class AdminDB(RegisterDB):

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)


    async def get_info(self, group_id: int) -> list[str]:
        stmt_grp = (
                select(Group)
                .options(selectinload(Group.contest))
                .where(Group.telegram_id == group_id)
                )
        stmt = (
                select(Contest)
                .join(Group)
                .where(Group.telegram_id == group_id)
                .order_by(Contest.id.desc()).limit(1)
                )
        count_photo = (
                select(func.count(group_photo.c.photo_id))
                .join(Group)
                .where(Group.telegram_id == group_id)
                )
        info_list = []
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                contest = (await session.scalars(stmt)).one() 
                info_list.append(contest.contest_name)
                photo_count = (await session.scalars(count_photo)).one_or_none()
                if photo_count is None:
                    photo_count = 0
                info_list.append(photo_count)
                group = (await session.scalars(stmt_grp)).one()
                if group.vote_in_progress is True:
                    stmt_count = (
                            select(func.count(contest_user.c.user_id))
                            .where(contest_user.c.contest_id == contest.id)
                            .group_by(contest_user.c.contest_id)
                            )
                    count_voted_users = (
                            await session.scalars(stmt_count)).one_or_none()
                    if count_voted_users is None:
                        count_voted_users = '0'
                    info_list.append(count_voted_users)
                return info_list

    async def change_contest_to_none(self, group_id: int) -> bool:
        ret: bool = False
        contest = ObjectFactory.build_contest("-1", 1)
        stmt = (
                select(Group)
                .where(Group.telegram_id == group_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                group = (await session.scalars(stmt)).one()
                contest.group_id = group.id
                contest = await session.merge(contest)

        return ret

    async def remove_photo(self, photo_file_id: str):
        #todo: tests
        stmt = (
                select(Photo)
                .where(Photo.file_id == photo_file_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                photo = (await session.scalars(stmt)).one()
                await session.delete(photo)
        return True

    async def change_current_vote_status(self, group_id: int) -> bool:
        ret: bool = False
        stmt = (
                select(Group)
                .where(Group.telegram_id == group_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                srch = await session.scalars(stmt)
                res = srch.one()
                if not res.vote_in_progress:
                    ret = res.vote_in_progress = True
                else:
                    ret = res.vote_in_progress = False

        return ret

    async def select_all_administrated_groups(self, telegram_user_id: int) -> list:
        ret: list = []
        stmt = (
                select(Group)
                .join(group_admin)
                .join(User)
                .where(User.telegram_id == telegram_user_id)
                )
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                ids = await session.scalars(stmt)
                for id in ids:
                    ret.append([id.name, id.telegram_id])

        return ret

    async def check_admin(self, user_id: int, group_id: int) -> bool:
        stmt = (
                select(User)
                .options(selectinload(User.groups))
                .join(group_admin,
                      (User.id == group_admin.c.user_id)
                      )
                .where(User.telegram_id == user_id)
                .where(group_admin.c.group_id == (
                    select(Group.id).where(Group.telegram_id == group_id)
                    ).scalar_subquery()))
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                srch = await session.scalars(stmt)
                admin = srch.one_or_none()
                return admin is not None

    async def set_contest_theme(self, group_id: int, theme: str,
                                contest_duration_sec=604800) -> str:
        stmt_g = (
                select(Group.id).where(Group.telegram_id == group_id)
                )
        theme_object = ObjectFactory.build_contest(theme, contest_duration_sec)
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                group_id = (await session.scalars(stmt_g)).one()
                theme_object.group_id = group_id
                session.add(theme_object)

        return f'Тема зарегистрирована. {theme}'
