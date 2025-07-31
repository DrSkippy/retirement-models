import unittest

from models.utils import *


class MyTestCase(unittest.TestCase):

    def test_utils_datetime_sequence(self):
        x = create_datetime_sequence("2020-01-01", "2020-06-01")
        self.assertEqual(len(x), 6)
        self.assertEqual(x[0].strftime("%Y-%m-%d"), "2020-01-01")
        self.assertEqual(x[-1].strftime("%Y-%m-%d"), "2020-06-01")


if __name__ == '__main__':
    unittest.main()
