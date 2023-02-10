from sqlalchemy import create_engine
from db.db_classes import Base
from db.db_operations import init_test_data, set_like_photo,\
        set_register_photo, get_like_photo, get_register_photo,\
        select_contest_photos
import unittest


class TestDb(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
        self.name = "Ivan"
        self.tg_id = "1919118841"
        self.group_id = "55145151"
        self.theme = "#текстуры"

        Base.metadata.create_all(self.engine)
        init_test_data(self.engine, self.name, self.tg_id, self.group_id)

    def test_get_list_contest_photo(self):
        ret = select_contest_photos(self.engine, self.group_id)
        res = []
        self.assertNotEqual(ret, res, "Should be not equal")

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

    def test_add_photo_for_contest(self):
        expected_link = get_register_photo(self.engine, self.tg_id)
        self.assertNotEqual(expected_link, "0", "Should be not 0")


if __name__ == '__main__':
    unittest.main()
