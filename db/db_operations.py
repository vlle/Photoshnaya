from sqlalchemy import exc
from sqlalchemy.sql.coercions import expect
from db.db_classes import User, Photo, Group, groupUser, groupPhoto
from sqlalchemy.orm import Session
from sqlalchemy import select

def set_like_photo_hash(engine, tg_id: str, hash: str):
    stmt = (
            select(Photo)
            .join(Photo.id)
            .where(User.telegram_id == tg_id)
            .where(Photo.hash == hash)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        photo = session.scalars(stmt).one() 
        try:
            photo.likes += 1
            likes = photo.likes
        except:
            pass
    return likes

def set_like_photo_single(engine, id: str) -> int:
    stmt = (
            select(Photo)
            .where(Photo.id == id)
            )
    likes = -1
    with Session(engine) as session, session.begin():
        #try:
        photo = session.scalars(stmt).one() 
        photo.likes += 1
        likes = photo.likes
        #except exc.NoResultFound:
        #    print("Error, no result found")
        #    pass
        #except exc.ArgumentError:
        #    print("Error, no set available found")
        #    pass
    return likes


def set_like_photo(engine, tg_id: str, hash = None):
    likes = -1
    if (hash is not None):
        likes = set_like_photo_hash(engine, tg_id, hash)
    else:
        likes = set_like_photo_single(engine, tg_id)
    return likes

def get_like_photo_single(engine, tg_id: str) -> int:
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
            #likes = user.likes
        except exc.NoResultFound:
            pass

    return likes

def get_like_photo_hash(engine, tg_id: str, hash: str) -> int:
    stmt = (
            select(Photo)
            .join(User)
            .where(User.telegram_id == tg_id)
            .where(Photo.hash == hash)
            )
    likes = 0
    with Session(engine) as session, session.begin():
        try:
            user = session.scalars(stmt).one() 
            likes = user.likes
        except exc.NoResultFound:
            pass

    return likes

def get_like_photo(engine, tg_id: str, hash = None) -> int:
    likes = -1
    if (hash is not None):
        likes = get_like_photo_hash(engine, tg_id, hash)
    else:
        likes = get_like_photo_single(engine, tg_id)
    return likes

def set_register_photo(engine, tg_id: str, grtg_id: str):
    stmt_sel = (
            select(User)
            .where(User.telegram_id == tg_id)
            )
    stmtG_sel = (
            select(Group)
            .where(Group.telegram_id == grtg_id)
            )
    with Session(engine) as session, session.begin():
        user = session.scalars(stmt_sel).one() 
        group = session.scalars(stmtG_sel).one() 
        try:
            photo = Photo(hash="hash", likes=0, user_id = user.id)
            user.photos.append(photo)
            group.photos.append(photo)
            session.add(photo)
        except:
            pass

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
            )
    with Session(engine) as session, session.begin():
        photos = session.scalars(stmtG)
        for photo in photos:
            print("ssSDasdasda")
            print(photo)
            ret.append(photo)
    #ret = []
    #stmtG = (
            #        select(Group)
            #        .join(Group.users)
            #        .join(User.photos)
            #        .where(Group.telegram_id == group_id)
            #        )
    #with Session(engine) as session, session.begin():
    #    group = session.scalars(stmtG).one()
    #    for a in group.users:
    #        print(a.photos)
    #        ret.append(a.photos)
    #    print("Been")
    return ret

def set_contest_winner(engine, user_id: str, photo_id: str):
    pass

def get_contest_winner(engine, user_id: str, photo_id: str):
    pass

def set_contest_theme(engine, user_id: str, photo_id: str):
    pass

def get_contest_theme(engine, user_id: str, photo_id: str):
    pass


def init_test_data(engine, name: str, usertg_id: str, tggroup_id: str):
    human = User(name=name, full_name= name + "Foobar", telegram_id = usertg_id)
    groupFrog = Group(name="Жабы", telegram_id = tggroup_id, contest_theme = "#пляжи")
    human.groups.append(groupFrog)
    with Session(engine) as session, session.begin():
        session.add(human)
        session.add(groupFrog)

    set_register_photo(engine, usertg_id, tggroup_id)
