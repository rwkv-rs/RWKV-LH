import unittest
from math_utils import safe_divide, median

class MathTests(unittest.TestCase):
    def test_divide(self):
        self.assertEqual(safe_divide(8,2),4)
        with self.assertRaises(ValueError): safe_divide(1,0)
    def test_median(self):
        source=[9,1,5,3]; self.assertEqual(median(source),4); self.assertEqual(source,[9,1,5,3])
        self.assertEqual(median([7,2,4]),4)

if __name__ == '__main__': unittest.main()
