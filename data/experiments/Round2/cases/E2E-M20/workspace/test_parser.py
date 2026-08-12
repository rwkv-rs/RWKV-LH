import unittest
from parser import parse_records

class ParserTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_records('1 | Ada | 9\n\n2|Lin|7\n'), [{'id':'1','name':'Ada','score':9},{'id':'2','name':'Lin','score':7}])
    def test_duplicate(self):
        with self.assertRaises(ValueError): parse_records('1|A|1\n1|B|2\n')

if __name__ == '__main__': unittest.main()
