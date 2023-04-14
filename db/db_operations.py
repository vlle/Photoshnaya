from sqlalchemy import exc
from db.db_classes import User, Photo, Group, groupUser, groupPhoto, groupAdmin
from sqlalchemy.orm import Session
from sqlalchemy import select

# Make Class!!


def register_group(engine, group: Group) -> str:
    if (find_group(engine, group.telegram_id) is True):
        return "Группа уже зарегистрирована. 😮"

    with Session(engine) as session, session.begin():
        session.add(group)

    return "Зарегистрировал группу. "


def register_user(engine, user: User, tg_group_id: str, group=None)\
        -> str:
    if (find_user_in_group(engine, user.telegram_id, tg_group_id)) is True:
        return "User was already registered"

    stmt = select(Group).where(Group.telegram_id == tg_group_id)
    with Session(engine) as session, session.begin():
        try:
            search_result = session.scalars(stmt).one()
        except exc.NoResultFound:
            register_group(engine, group)

        search_result = session.scalars(stmt).one()
        user.groups.append(search_result)
        session.add(user)

    return "User was added"


def find_user(engine, user_tg: str) -> bool:
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


def find_group(engine, telegram_id: str) -> bool:
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


def find_user_in_group(engine, telegram_user_id, group_telegram_id) -> bool:
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
            .where(groupUser.c.user_id == (
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

    return ret


def set_like_photo(engine, photo_id: str):
    stmt = (
            select(Photo)
            .where(Photo.id == photo_id)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one()
        photo.likes += 1
        likes = photo.likes
    return likes


def get_like_photo(engine, tg_id: str) -> int:
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


def set_register_photo(engine, tg_id: str, grtg_id: str,
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
        photo = Photo(likes=0, file_id=file_get_id, user_id=user.id)
        user.photos.append(photo)
        group.photos.append(photo)
        session.add(photo)


def get_register_photo(engine, tg_id: str) -> int:
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


def select_contest_photos(engine, group_id: str) -> list:
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


def select_contest_photos_ids(engine, group_id: str) -> list:
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

def select_next_contest_photo(engine, group_id: str, current_photo: int) -> list[str]:
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
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for i in photos:
            print(i)
        photos = session.scalars(stmtG).first()
        if (photos):
            print(photos)
            ret.append(photos.file_id)
            ret.append(photos.id)
    return ret


def set_contest_winner(engine, user_id: str, photo_id: str):
    pass


def get_contest_winner(engine, user_id: str, photo_id: str):
    pass


def set_contest_theme(engine, user_id: str, group_id: str, theme: str, contest_duration_sec = 604800) -> str:
    stmt = (
            select(Group)
            .join(groupAdmin,
                  (Group.id == groupAdmin.c.group_id)
                  )
            .join(User,
                  (User.id == groupAdmin.c.user_id)
                  )
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
            group[0].contest_theme = theme
            ret_msg = "Кое-что задублировалось, но тему поменял."

    return ret_msg


def get_contest_theme(engine, group_id: str):
    stmt = (
        select(Group)
        .where(Group.telegram_id == group_id)
    )
    theme = "Без темы?"
    with Session(engine) as session, session.begin():
        try:
            group = session.scalars(stmt).one()
        except exc.NoResultFound:
            theme = "Ошибка, не нашел группу."
        theme = group.contest_theme
    return theme


def build_group(name: str, telegram_id: str, contest_theme: str, contest_duration_sec=None) -> Group:
    if (contest_duration_sec):
        groupFrog = Group(name=name, telegram_id=telegram_id,
                          contest_theme=contest_theme, contest_duration_sec=contest_duration_sec)
    else:
        groupFrog = Group(name=name, telegram_id=telegram_id,
                          contest_theme=contest_theme, contest_duration_sec=604800)
    return groupFrog


def build_user(name: str, full_name: str, user_id: str) -> User:
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

def register_admin(engine, adm_user: User, group_id: str, group=None):
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


def get_admins(engine, group_id) -> list:
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


def check_admin(engine, user_id: str, group_id: str) -> bool:
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
            return False
        except exc.MultipleResultsFound:
            admin_right = True

    return admin_right


def register_user_and_group(engine, group: Group,
                            user: User, group_telegram_id: str) -> str:
    message = "None yet"
    register_group(engine, group)
    register_user(engine, user, group_telegram_id)
    return message


def init_test_data(engine, name: str, usertg_id: str, tggroup_id: str):
    group = build_group(name, tggroup_id, "отсутствует")
    user = build_user(name, name+" Foobar", usertg_id)
    register_user_and_group(engine, group, user, tggroup_id)

    set_register_photo(engine, usertg_id, tggroup_id)
