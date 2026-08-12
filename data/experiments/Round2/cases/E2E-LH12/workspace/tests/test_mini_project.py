import json, unittest
from mini_project.parser import parse_lines
from mini_project.analyzer import summarize
from mini_project.reporter import render

class MiniProjectTests(unittest.TestCase):
    def test_pipeline(self):
        lines = parse_lines(' alpha \n\nbeta\nalpha\n')
        self.assertEqual(lines, ['alpha', 'beta', 'alpha'])
        summary = summarize(lines)
        self.assertEqual(summary, {'count': 3, 'unique_count': 2, 'longest': 'alpha'})
        self.assertEqual(json.loads(render(summary)), summary)
        self.assertTrue(render(summary).endswith('\n'))

if __name__ == '__main__': unittest.main()
