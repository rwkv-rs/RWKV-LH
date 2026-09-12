from types import SimpleNamespace
import pytest
from rwkv_lh.model import LongHorizonModel

def test_advice_is_not_acceptance_and_preserves_visible_evidence():
 from rwkv_lh.summary_advice import build_advice_request,make_advice_event
 goal=LongHorizonModel.create_literal_goal('Summarize the specified file.','.')
 request=build_advice_request(goal,{'server.py':'ORIGINAL SOURCE'},'ORIGINAL ANSWER')
 assert request['files']=={'server.py':'ORIGINAL SOURCE'}
 assert request['candidate']=='ORIGINAL ANSWER'
 event=make_advice_event('E1','Advice exactly','external_strong_model','model-id')
 assert event.payload['advice']=='Advice exactly'
 assert event.payload['is_execution_evidence'] is False
 assert 'not accepted' not in event.payload['instruction']

def test_advice_rejects_extra_keys_without_repair():
 from rwkv_lh.summary_advice import request_advice
 client=SimpleNamespace(_request_json=lambda **kw:{'advice':'x','final_answer':'invented'})
 goal=LongHorizonModel.create_literal_goal('Summarize.','.')
 with pytest.raises(ValueError):request_advice(client,goal,{'f':'source'},'answer','run',4096)

def test_advice_transport_gets_only_registered_request():
 from rwkv_lh.summary_advice import request_advice
 seen=[]
 def call(**kw):seen.append(kw);return {'advice':'原样建议'}
 goal=LongHorizonModel.create_literal_goal('Summarize.','.')
 assert request_advice(SimpleNamespace(_request_json=call),goal,{'f':'source'},'answer','run',4096)=='原样建议'
 assert seen[0]['max_tokens']==4096
 assert set(seen[0]['request_payload'])=={'protocol','goal','files','candidate'}
