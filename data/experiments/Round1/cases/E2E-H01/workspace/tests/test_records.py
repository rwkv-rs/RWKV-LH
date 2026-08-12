import unittest
from package.records import load_records, summarize

class RecordTests(unittest.TestCase):
    def test_load_and_summary(self):
        records = load_records('example.csv')
        self.assertEqual(records, [{'name':'A','value':3}, {'name':'B','value':5}, {'name':'A','value':2}])
        self.assertEqual(summarize(records), {'count':3,'total':10,'by_name':{'A':5,'B':5}})

if __name__ == '__main__':
    unittest.main()
