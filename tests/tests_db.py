from sqlalchemy import MetaData, create_engine
from db.db_classes import User, Base, Photo
from db.db_operations import init_test_data, set_like_photo, set_register_photo, get_like_photo, get_register_photo 
import unittest


class TestDb(unittest.TestCase):


    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
        self.name = "Ivan"
        self.tg_id = "1919118841"
        self.theme = "#текстуры"

        Base.metadata.create_all(self.engine)
        init_test_data(self.engine, self.name, self.tg_id)


    def test_get_like_photo(self):
        set_register_photo(self.engine, self.tg_id)
        likes = get_like_photo(self.engine, self.tg_id)
        self.assertEqual(likes, 0, "Should be 0")

    def test_set_like_photo(self):
        set_register_photo(self.engine, self.tg_id)
        likes = get_like_photo(self.engine, self.tg_id)
        new_likes = set_like_photo(self.engine, self.tg_id)
        self.assertEqual(likes + 1, new_likes, "Should be likes + 1")

    def test_remove_like_photo(self):
        #self.assertEqual(sum((1, 2, 3)), 6, "Should be 6")
        pass
    def test_only_one_user_add(self):
        pass

    def test_add_photo_for_contest(self):
        expected_link = get_register_photo(self.engine, self.tg_id)
        self.assertNotEqual(expected_link, "0", "Should be not 0")


if __name__ == '__main__':
    unittest.main()
