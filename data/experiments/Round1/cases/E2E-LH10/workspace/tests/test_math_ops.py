import unittest
from src.math_ops import mean, clamp

class MathOpsTests(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean([2, 4, 6]), 4)
        self.assertEqual(mean([5]), 5)
    def test_clamp(self):
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-2, 0, 10), 0)
        self.assertEqual(clamp(20, 0, 10), 10)

if __name__ == '__main__': unittest.main()
