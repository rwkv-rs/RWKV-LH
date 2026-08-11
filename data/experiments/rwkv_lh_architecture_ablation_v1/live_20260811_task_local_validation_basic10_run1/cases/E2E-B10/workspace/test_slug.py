import unittest
from slug import slugify

class SlugTests(unittest.TestCase):
    def test_words(self):
        self.assertEqual(slugify('Hello RWKV World'), 'hello-rwkv-world')

    def test_spacing(self):
        self.assertEqual(slugify('  Multiple   Spaces  '), 'multiple-spaces')

if __name__ == '__main__':
    unittest.main()
