from sqlalchemy import create_engine
from db.db_classes import Base
from db.db_operations import build_group, find_user, init_test_data, register_group, set_like_photo,\
        set_register_photo, get_like_photo, get_register_photo,\
        select_contest_photos, find_user, find_user_in_group, \
        build_group, register_group, set_contest_theme, \
        register_admin, build_user, get_contest_theme
import unittest


class TestDb(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
        self.name = "Ivan"
        self.tg_id = "1919118841"
        self.group_id = "55145151"
        self.theme = "#текстуры"
        self.ad_name = "IvanCool"
        self.ad_tg_id = "1919118842"

        Base.metadata.create_all(self.engine)
        init_test_data(self.engine, self.name, self.tg_id, self.group_id)
        ad = build_user(self.ad_name, self.ad_name+"Full", self.ad_tg_id)
        register_admin(self.engine, ad, self.group_id)

    def test_get_list_contest_photo(self):
        ret = select_contest_photos(self.engine, self.group_id)
        self.assertTrue(ret, "Should be not empty ")

    def test_get_speicif_list_contest_photo(self):
        group = build_group("foo", "123", "None")
        register_group(self.engine, group)
        group = build_group("bar", "321", "None")
        register_group(self.engine, group)
        set_register_photo(self.engine, self.tg_id, "123")
        set_register_photo(self.engine, self.tg_id, "123")
        set_register_photo(self.engine, self.tg_id, "321")
        set_register_photo(self.engine, self.tg_id, "321")
        set_register_photo(self.engine, self.tg_id, "321")
        set_register_photo(self.engine, self.tg_id, "321")
        set_register_photo(self.engine, self.tg_id, self.group_id)
        set_register_photo(self.engine, self.tg_id, self.group_id)
        ret = select_contest_photos(self.engine, self.group_id)
        assert len(ret) == 3

    def test_get_listMany_contest_photo(self):
        set_register_photo(self.engine, self.tg_id, self.group_id)
        set_register_photo(self.engine, self.tg_id, self.group_id)
        ret = select_contest_photos(self.engine, self.group_id)
        self.assertEqual(len(ret), 3, "Should be equal")

    def test_get_like_photo(self):
        set_register_photo(self.engine, self.tg_id, self.group_id)
        likes = get_like_photo(self.engine, self.tg_id)
        self.assertEqual(likes, 0, "Should be 0")

    def test_set_like_photo(self):
        set_register_photo(self.engine, self.tg_id, self.group_id)
        likes = get_like_photo(self.engine, self.tg_id)
        new_likes = set_like_photo(self.engine, 1)  # photo.id!!!
        new_likes = set_like_photo(self.engine, 1)  # photo.id!!!
        self.assertEqual(likes + 2, new_likes, "Should be likes + 1")

    def test_remove_like_photo(self):
        pass

    def test_only_one_user_add(self):
        pass

    def test_find_user(self):
        self.assertTrue(find_user(self.engine, self.tg_id))

    def test_find_user_in_group(self):
        self.assertTrue(
                find_user_in_group(self.engine, self.tg_id, self.group_id))

    def test_find_no_user_in_group(self):
        self.assertFalse(find_user_in_group(
            self.engine, self.tg_id+"empty", self.group_id))

    def test_add_photo_for_contest(self):
        expected_link = get_register_photo(self.engine, self.tg_id)
        self.assertNotEqual(expected_link, "0", "Should be not 0")

    def test_set_contest_theme(self):
        self.theme = "#текстуры"
        assert self.theme == set_contest_theme(self.engine,
                                               self.ad_tg_id,
                                               self.group_id,
                                               self.theme)

    def test_get_contest_theme(self):
        self.theme = "#пляжи"
        set_contest_theme(self.engine,
                          self.ad_tg_id,
                          self.group_id,
                          self.theme)
        assert self.theme == get_contest_theme(self.engine, self.group_id)


if __name__ == '__main__':
    unittest.main()
