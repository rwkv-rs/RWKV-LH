import unittest
from src.consumer import compute

class ConsumerTests(unittest.TestCase):
    def test_compute(self):
        self.assertEqual(compute(4), (8, 'old_api documentation'))

if __name__ == '__main__':
    unittest.main()
