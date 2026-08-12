import unittest
from queueing import TaskQueue

class QueueTests(unittest.TestCase):
    def test_order(self):
        q=TaskQueue(); q.add('b',2); q.add('a',2); q.add('c',5)
        self.assertEqual([q.pop(),q.pop(),q.pop()], ['c','a','b'])
    def test_duplicate(self):
        q=TaskQueue(); q.add('x',1)
        with self.assertRaises(ValueError): q.add('x',9)

if __name__ == '__main__': unittest.main()
