# https://github.com/OCCCAS/aiogram_tests

import pytest
from sqlalchemy import create_engine
from db.db_classes import Base
from db.db_operations import build_group, find_user, init_test_data, register_group, set_like_photo,\
        set_register_photo, get_like_photo, get_register_photo,\
        select_contest_photos, find_user, find_user_in_group, \
        build_group, register_group, build_user, register_user, \
        register_admin, get_admins


class BaseFixture:
    def __init__(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
        self.group_name = "test_group"
        self.group_id = "995"
        self.username = "foobar"
        self.user_fullname = "foobar foobarovich"
        self.user_id = "559"
        Base.metadata.create_all(self.engine)
        init_test_data(self.engine, self.username, self.user_id, self.group_id)


def test_admin_add():
    message = BaseFixture()
    msg = "Добавили в чат, здоров!"
    group = build_group(message.group_name, message.group_id, "none")
    reg_msg = register_group(message.engine, group)
    adm_user = build_user(message.username,
                              message.user_fullname,
                              message.user_id)
    
    success_message = "Добавил администратора."
    assert success_message == register_admin(message.engine, 
                                             adm_user, 
                                             str(message.group_id))

def test_admin_get():
    message = BaseFixture()
    msg = "Добавили в чат, здоров!"
    group = build_group(message.group_name, message.group_id, "none")
    reg_msg = register_group(message.engine, group)
    adm_user = build_user(message.username,
                              message.user_fullname,
                              message.user_id)
    register_admin(message.engine,
                   adm_user,
                   str(message.group_id))
    assert 1 == len(get_admins(message.engine, message.group_id))
