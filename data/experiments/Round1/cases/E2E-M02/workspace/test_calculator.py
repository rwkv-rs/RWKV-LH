import unittest
from calculator import weighted_total

class CalculatorTests(unittest.TestCase):
    def test_weighted_total(self):
        self.assertEqual(weighted_total([(10, 2), (5, 3)]), 35)

    def test_empty(self):
        self.assertEqual(weighted_total([]), 0)

if __name__ == '__main__':
    unittest.main()
