from sqlalchemy import exc
from db.db_classes import TemporaryPhotoLike, User, Photo, Group, groupUser, groupPhoto, groupAdmin
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from sqlalchemy import Engine

# Make Class!!

class ObjectFactory():

    def __init__(self) -> None:
        pass

    def build_group(self, name: str, telegram_id: int, contest_theme: str, contest_duration_sec=None) -> Group:
        if (contest_duration_sec):
            group = Group(name=name, telegram_id=telegram_id,
                              contest_theme=contest_theme, contest_duration_sec=contest_duration_sec)
        else:
            group = Group(name=name, telegram_id=telegram_id,
                              contest_theme=contest_theme, contest_duration_sec=604800)
        return group
    
    
    def build_user(self, name: str, full_name: str, user_id: int) -> User:
        human = User(name=name, full_name=full_name, telegram_id=user_id)
        return human



class BaseDb():

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        
class Like(BaseDb):

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine)

    def like_photo(self, tg_id: int, id: int) -> int:
        srch_stmt_photo = select(Photo).where(Photo.id == id)
        srch_stmt_user = select(User).where(User.telegram_id == tg_id)
        likes = 0
        with Session(self.engine) as session, session.begin():
            user = session.scalars(srch_stmt_user).one()
            photo = session.scalars(srch_stmt_photo).one()
            tmp_like = TemporaryPhotoLike(likes_t=photo.id, liked_t=user.id)
            session.add(tmp_like)

        return likes

    def remove_like_photo(self, tg_id: int, id: int) -> None:
        stmt = (
                delete(TemporaryPhotoLike)
                .where(TemporaryPhotoLike.liked_t==(select(User.id).where(User.telegram_id == tg_id).scalar_subquery())
                & (TemporaryPhotoLike.likes_t==id)
                ))
        with Session(self.engine) as session, session.begin():
            session.execute(stmt)


    def is_photo_liked(self, tg_id: int, file_id: str) -> int:
        stmt = (
                select(TemporaryPhotoLike)
                .join(User, TemporaryPhotoLike.liked_t == User.id)
                .join(Photo, TemporaryPhotoLike.likes_t == Photo.id)
                .where(User.telegram_id == tg_id)
                .where(Photo.file_id == file_id)
                )
        likes = 0
        with Session(self.engine) as session, session.begin():
            like = session.scalars(stmt).fetchall()
            for _ in like:
                likes += 1
    
        return likes

    def select_next_contest_photo(self, group_id: int, current_photo: int) -> list[str]:
        ret = []
        stmtG = (
                select(Photo)
                .join(
                    groupPhoto,
                    (Photo.id == groupPhoto.c.photo_id)
                    )
                .where(
                    (groupPhoto.c.group_id == (
                        select(Group.id)
                        .where(Group.telegram_id == group_id).scalar_subquery())
                     ) &
                    (Photo.id > current_photo))
                .order_by(Photo.id)
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmtG).first()
            if (photos):
                ret.append(photos.file_id)
                ret.append(photos.id)
        return ret

    def select_prev_contest_photo(self, group_id: int, current_photo: int) -> list[str]:
        ret = []
        stmtG = (
                select(Photo)
                .join(
                    groupPhoto,
                    (Photo.id == groupPhoto.c.photo_id)
                    )
                .where(
                    (groupPhoto.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_id).scalar_subquery())
                       ) &
                       (Photo.id < current_photo))
                .order_by(Photo.id.desc())
                )
        with Session(self.engine) as session, session.begin():
            photos = session.scalars(stmtG).first()
            photos = session.scalars(stmtG).first()
            if (photos):
                ret.append(photos.file_id)
                ret.append(photos.id)
        return ret


class Register(BaseDb):

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine)


    def register_group(self, group: Group) -> tuple:
        if (find_group(self.engine, group.telegram_id) is True):
            return "Группа уже зарегистрирована. 😮", False
    
        with Session(self.engine) as session, session.begin():
            session.add(group)
    
        return "Зарегистрировал группу. ", True
    
    
    def register_user(self, user: User, tg_group_id: int, group=None)\
            -> str:
        if (find_user_in_group(self.engine, user.telegram_id, tg_group_id)) is True:
            return "User was already registered"
    
        stmt = select(Group).where(Group.telegram_id == tg_group_id)
        with Session(self.engine) as session, session.begin():
            try:
                search_result = session.scalars(stmt).one()
            except exc.NoResultFound:
                if group is not None:
                    register_group(self.engine, group)
                else:
                    raise ValueError
    
            search_result = session.scalars(stmt).one()
            user.groups.append(search_result)
            session.add(user)
    
        return "User was added"

    def register_admin(self, adm_user: User, group_id: int, group=None):
        stmt = select(Group).where(Group.telegram_id == group_id)
        with Session(self.engine) as session, session.begin():
            try:
                search_result = session.scalars(stmt).one()
            except exc.NoResultFound:
                if (group):
                    register_group(self.engine, group)
    
            search_result = session.scalars(stmt).one()
            adm_user.admin_in.append(search_result)
            adm_user.groups.append(search_result)
            session.add(adm_user)
    
        return "Добавил администратора."

    def set_register_photo(self, tg_id: int, grtg_id: int,
                           file_get_id='-1', user_p=None, group_p=None):
        stmt_sel = (
                select(User)
                .where(User.telegram_id == tg_id)
                )
        stmtG_sel = (
                select(Group)
                .where(Group.telegram_id == grtg_id)
                )
        with Session(self.engine) as session, session.begin():
            try:
                user = session.scalars(stmt_sel).one()
                group = session.scalars(stmtG_sel).one()
            except exc.NoResultFound:
                if (user_p):
                    self.register_user(user_p, grtg_id, group_p)
                if (group_p):
                    self.register_group(group_p)
    
            user = session.scalars(stmt_sel).one()
            group = session.scalars(stmtG_sel).one()
            photo = Photo(file_id=file_get_id, user_id=user.id)
            user.photos.append(photo)
            group.photos.append(photo)
            session.add(photo)


class Select(BaseDb):
    pass


def register_group(engine, group: Group) -> str:
    if (find_group(engine, group.telegram_id) is True):
        return "Группа уже зарегистрирована. 😮"

    with Session(engine) as session, session.begin():
        session.add(group)

    return "Зарегистрировал группу. "


def register_user(engine, user: User, tg_group_id: int, group=None)\
        -> str:
    if (find_user_in_group(engine, user.telegram_id, tg_group_id)) is True:
        return "User was already registered"

    stmt = select(Group).where(Group.telegram_id == tg_group_id)
    with Session(engine) as session, session.begin():
        try:
            search_result = session.scalars(stmt).one()
        except exc.NoResultFound:
            if group is not None:
                register_group(engine, group)
            else:
                raise ValueError

        search_result = session.scalars(stmt).one()
        user.groups.append(search_result)
        session.add(user)

    return "User was added"


def find_user(engine, user_tg: int) -> bool:
    stmt = (
            select(User)
            .where(User.telegram_id == user_tg)
            )
    search_result = None
    with Session(engine) as session, session.begin():
        try:
            search = session.scalars(stmt).one()
            search_result = search is not None
        except exc.NoResultFound:
            search_result = False

    return search_result


def find_group(engine, telegram_id: int) -> bool:
    stmt = (
            select(Group)
            .where(Group.telegram_id == telegram_id)
            )
    search_result = True
    with Session(engine) as session, session.begin():
        try:
            search = session.scalars(stmt).one()
            search_result = search is not None
        except exc.NoResultFound:
            search_result = False

    return search_result


def find_user_in_group(engine, telegram_user_id: int, group_telegram_id: int) -> bool:
    stmt = (
            select(User)
            .join(
                groupUser,
                (User.id == groupUser.c.user_id)
                )
            .where(groupUser.c.group_id == (
                select(Group.id)
                .where(Group.telegram_id == group_telegram_id)
                .scalar_subquery()))
            .where(groupUser.c.user_id.in_(
                select(User.id)
                .where(User.telegram_id == telegram_user_id)
                .scalar_subquery()))
         )
    ret = False
    with Session(engine) as session, session.begin():
        try:
            search_result = session.scalars(stmt).one()
            ret = search_result is not None
        except exc.NoResultFound:
            ret = False
        except exc.MultipleResultsFound:
            ret = True

    print(ret)
    return ret


def set_like_photo(engine, photo_id: int):
    stmt = (
            select(Photo)
            .where(Photo.id == photo_id)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one()
        #photo.likes += 1
        likes = photo.likes
    return likes


def get_like_photo(engine, tg_id: int) -> int:
    # in specific group? or what?
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    likes = 0
    with Session(engine) as session, session.begin():
        try:
            photos = session.scalars(stmt)
            for i in photos:
                print(i)
        except exc.NoResultFound:
            pass

    return likes


def set_register_photo(engine, tg_id: int, grtg_id: int,
                       file_get_id='-1', user_p=None, group_p=None):
    stmt_sel = (
            select(User)
            .where(User.telegram_id == tg_id)
            )
    stmtG_sel = (
            select(Group)
            .where(Group.telegram_id == grtg_id)
            )
    with Session(engine) as session, session.begin():
        try:
            user = session.scalars(stmt_sel).one()
            group = session.scalars(stmtG_sel).one()
        except exc.NoResultFound:
            if (user_p):
                register_user(engine, user_p, grtg_id, group_p)
            if (group_p):
                register_group(engine, group_p)

        user = session.scalars(stmt_sel).one()
        group = session.scalars(stmtG_sel).one()
        photo = Photo(file_id=file_get_id, user_id=user.id)
        user.photos.append(photo)
        group.photos.append(photo)
        session.add(photo)


def get_register_photo(engine, tg_id: int) -> int:
    id = -1
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            )
    with Session(engine) as session, session.begin():
        try:
            photo = session.scalars(stmt).one()
            id = photo.id
        except exc.NoResultFound:
            pass

    return id


def unregister_photo(engine, user_id: str, photo_id: str):
    pass


def select_contest_photos(engine, group_id: int) -> list:
    ret = []
    stmtG = (
            select(Photo)
            .join(
                groupPhoto,
                (Photo.id == groupPhoto.c.photo_id)
                )
            .where(groupPhoto.c.group_id == (
                select(Group.id)
                .where(Group.telegram_id == group_id).scalar_subquery()))
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for photo in photos:
            print(photo)
            ret.append(photo)
    return ret


def select_contest_photos_ids(engine, group_id: int) -> list:
    ret = []
    stmtG = (
            select(Photo)
            .join(
                groupPhoto,
                (Photo.id == groupPhoto.c.photo_id)
                )
            .where(groupPhoto.c.group_id == (
                select(Group.id)
                .where(Group.telegram_id == group_id).scalar_subquery()))
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for photo in photos:
            ret.append(photo.file_id)
    return ret

def select_prev_contest_photo(engine, group_id: int, current_photo: int) -> list[str]:
    ret = []
    stmtG = (
            select(Photo)
            .join(
                groupPhoto,
                (Photo.id == groupPhoto.c.photo_id)
                )
            .where(
                (groupPhoto.c.group_id == (
                select(Group.id)
                .where(Group.telegram_id == group_id).scalar_subquery())
                   ) &
                   (Photo.id < current_photo))
            .order_by(Photo.id.desc())
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG).first()
        photos = session.scalars(stmtG).first()
        if (photos):
            ret.append(photos.file_id)
            ret.append(photos.id)
    return ret

def select_file_id(engine, group_id: int, current_photo: int) -> str:
    ret = ''
    stmtG = (
            select(Photo)
            .where(
                (Photo.id == current_photo))
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG).first()
        if (photos):
            ret = photos.file_id
    return ret

def select_next_contest_photo(engine, group_id: int, current_photo: int) -> list[str]:
    ret = []
    stmtG = (
            select(Photo)
            .join(
                groupPhoto,
                (Photo.id == groupPhoto.c.photo_id)
                )
            .where(
                (groupPhoto.c.group_id == (
                    select(Group.id)
                    .where(Group.telegram_id == group_id).scalar_subquery())
                 ) &
                (Photo.id > current_photo))
            .order_by(Photo.id)
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG).first()
        if (photos):
            ret.append(photos.file_id)
            ret.append(photos.id)
    return ret


def set_contest_winner(engine, user_id: str, photo_id: str):
    pass


def get_contest_winner(engine, user_id: str, photo_id: str):
    pass


def set_contest_theme(engine, user_id: int, group_id: int, theme: str, contest_duration_sec = 604800) -> str:
    stmt = (
            select(Group)
            .join(groupAdmin,
                  (Group.id == groupAdmin.c.group_id)
                  )
            .join(User,
                  (User.id == groupAdmin.c.user_id)
                  )
            .where(Group.telegram_id == group_id)
            )
    ret_msg = None
    with Session(engine) as session, session.begin():
        try:
            group = session.scalars(stmt).one()
            group.contest_theme = theme
            group.contest_duration_sec = contest_duration_sec
            ret_msg = theme
        except exc.NoResultFound:
            ret_msg = "Ошибка, не нашел группу."

        except exc.MultipleResultsFound:
            group = session.scalars(stmt)
            for i in group:
                print(i)
            #group[0].contest_theme = theme
            ret_msg = "Кое-что задублировалось, но тему поменял."

    return ret_msg


def get_contest_theme(engine, group_id: int):
    stmt = (
            select(Group)
            .where(Group.telegram_id == group_id)
            )
    theme = "Без темы?"
    with Session(engine) as session, session.begin():
        try:
            group = session.scalars(stmt).one()
            theme = group.contest_theme
        except exc.NoResultFound:
            theme = "Ошибка, не нашел группу."
    return theme


def build_group(name: str, telegram_id: int, contest_theme: str, contest_duration_sec=None) -> Group:
    if (contest_duration_sec):
        groupFrog = Group(name=name, telegram_id=telegram_id,
                          contest_theme=contest_theme, contest_duration_sec=contest_duration_sec)
    else:
        groupFrog = Group(name=name, telegram_id=telegram_id,
                          contest_theme=contest_theme, contest_duration_sec=604800)
    return groupFrog


def build_user(name: str, full_name: str, user_id: int) -> User:
    human = User(name=name, full_name=full_name, telegram_id=user_id)
    return human

def build_theme(user_theme: list[str]) -> str:
    if (user_theme[1][0] != '#'):
        theme = '#' + user_theme[1]
    else:
        theme = '#'
        for let in user_theme[1]: 
            if let == '#':
                continue
            theme += let

    return theme

def register_admin(engine, adm_user: User, group_id: int, group=None):
    stmt = select(Group).where(Group.telegram_id == group_id)
    with Session(engine) as session, session.begin():
        try:
            search_result = session.scalars(stmt).one()
        except exc.NoResultFound:
            if (group):
                register_group(engine, group)

        search_result = session.scalars(stmt).one()
        adm_user.admin_in.append(search_result)
        adm_user.groups.append(search_result)
        session.add(adm_user)

    return "Добавил администратора."


def get_admins(engine, group_id: int) -> list:
    stmt = (
            select(User)
            .join(groupAdmin,
                  (User.id == groupAdmin.c.user_id)
                  )
            .where(groupAdmin.c.group_id == (
                select(Group.id).where(Group.telegram_id == group_id)
                ).scalar_subquery()))
    admin_list = []
    with Session(engine) as session, session.begin():
        search_result = session.scalars(stmt)
        for admin in search_result:
            admin_list.append(admin)

    return admin_list


def check_admin(engine, user_id: int, group_id: int) -> bool:
    admin_right = False
    stmt = (
            select(User)
            .join(groupAdmin,
                  (User.id == groupAdmin.c.user_id)
                  )
            .where(groupAdmin.c.group_id == (
                select(Group.id).where(Group.telegram_id == group_id)
                ).scalar_subquery()))
    with Session(engine) as session, session.begin():
        try:
            admin = session.scalars(stmt).one()
            if user_id == admin.telegram_id:
                admin_right = True
        except exc.NoResultFound:
            pass
        except exc.MultipleResultsFound:
            admin_right = True

    return admin_right


def register_user_and_group(engine, group: Group,
                            user: User, group_telegram_id: int) -> str:
    message = "None yet"
    register_group(engine, group)
    register_user(engine, user, group_telegram_id)
    return message


def init_test_data(engine, name: str, usertg_id: int, tggroup_id: int):
    group = build_group(name, tggroup_id, "отсутствует")
    user = build_user(name, name+" Foobar", usertg_id)
    register_user_and_group(engine, group, user, tggroup_id)

    set_register_photo(engine, usertg_id, tggroup_id)
