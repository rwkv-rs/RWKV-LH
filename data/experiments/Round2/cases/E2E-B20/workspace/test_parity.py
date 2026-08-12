import unittest
from parity import is_even

class ParityTests(unittest.TestCase):
    def test_values(self):
        self.assertTrue(is_even(0)); self.assertTrue(is_even(-4)); self.assertFalse(is_even(7))
    def test_bool_result(self):
        self.assertIs(type(is_even(2)), bool)

if __name__ == '__main__': unittest.main()
