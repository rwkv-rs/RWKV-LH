import unittest
from names import normalize_name

class NameTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_name('  Alpha   Beta '), 'alpha-beta')
        self.assertEqual(normalize_name('RWKV'), 'rwkv')

if __name__ == '__main__': unittest.main()
