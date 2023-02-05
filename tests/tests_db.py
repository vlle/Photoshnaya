from sqlalchemy import MetaData, create_engine
from db.db_classes import User, Base, Photos
from db.db_operations import get_like_photo, init_test_data, set_like_photo
import unittest


class TestDb(unittest.TestCase):

    def test_like_photo(self):
        engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
        metadata_obj = MetaData()
        Base.metadata.create_all(engine)
        name = "Ivan"
        tg_id = "1241"
        init_test_data(engine, name, tg_id)
        ans = get_like_photo(engine, name, tg_id)
        set_like_photo(engine, name, tg_id)
        expected = get_like_photo(engine, name, tg_id)
        self.assertEqual(ans + 1, expected, "Should be 6")

    def test_remove_like_photo(self):
        pass
        #self.assertEqual(sum((1, 2, 3)), 6, "Should be 6")

    def test_add_photo_for_contest(self):
        pass
        #self.assertEqual(sum((1, 2, 3)), 6, "Should be 6")

    # def test_add_photo_for_contest(self):
    #     self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")

if __name__ == '__main__':
    unittest.main()
