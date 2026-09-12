from pathlib import Path
import json,unittest
from validate_single_read_fixture_r2_20260912 import validate_fixture
R=Path('/home/chase/GitHub/RWKV-LH')
REG=json.loads((R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912/REGISTRATION.json').read_text())
class FixtureRegression(unittest.TestCase):
 def test_historical_missing_result_rejects_later_created_file(self):
  case=next(c for c in REG['cases'] if c['id']=='missing-2')
  with self.assertRaisesRegex(ValueError,'missing-file fixture contains target'):
   validate_fixture(case,R)
 def test_other_seven_frozen_fixtures_match_historical_results(self):
  for c in REG['cases']:
   if c['id']!='missing-2':validate_fixture(c,R)
if __name__=='__main__':unittest.main()
