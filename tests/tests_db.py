from sqlalchemy import MetaData, create_engine
from db.db_classes import User, Base, Photos
import unittest


class TestDb(unittest.TestCase):

    engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
    metadata_obj = MetaData()
    Base.metadata.create_all(engine)

    def test_like_photo(self):
        self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    def test_remove_like_photo(self):
        self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")

    def test_add_photo_for_contest(self):
        self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")

    # def test_add_photo_for_contest(self):
    #     self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")

if __name__ == '__main__':
    unittest.main()
