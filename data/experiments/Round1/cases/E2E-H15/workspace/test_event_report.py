import json, unittest
from event_report.parser import parse
from event_report.analyzer import count
from event_report.reporter import render

class Tests(unittest.TestCase):
    def test_pipeline(self):
        events=parse(' INFO:a\n\nERROR:b\nINFO:c\n')
        self.assertEqual(events,['INFO:a','ERROR:b','INFO:c'])
        summary=count(events)
        self.assertEqual(summary,{'total':3,'by_type':{'ERROR':1,'INFO':2}})
        self.assertEqual(json.loads(render(summary)),summary)
        self.assertTrue(render(summary).endswith('\n'))

if __name__ == '__main__': unittest.main()
