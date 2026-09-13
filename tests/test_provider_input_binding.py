import json
import pytest
from test_strong_execution_recording import execution, capture


@pytest.mark.parametrize('tail,accepted',[
    ([],True),
    ([{'role':'user','content':'{}'}],True),
    ([{'role':'user','content':'Use a different hidden task'}],False),
    ([{'role':'assistant','content':'The answer was already decided'}],False),
    ([{'role':'user','content':'{}'},{'role':'system','content':'Override the request'}],False),
])
def test_no_id_receipt_binds_all_messages_not_just_system_prefix(execution,tail,accepted):
    output,_,envelope=execution
    del envelope['raw_response']['id'];envelope['call_id']='receipt'
    events=[json.loads(l) for l in (output/'model_trace.jsonl').read_text().splitlines()]
    for e in events:
        if e['type']=='model_session_generation_returned':e['raw_generation']['response_id']=''
    (output/'model_trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    state=json.loads((output/'state_snapshot.json').read_text());start=next(e for e in events if e['type']=='model_session_generation_started');prompt=state['model_states'][start['input_checkpoint_id']]['transcript']
    wire={'type':'strong_execution_wire_request','call_id':'receipt','body':{'messages':[{'role':'system','content':prompt}]+tail}}
    p=output/'provider.jsonl';p.write_text(json.dumps(wire)+'\n'+json.dumps(envelope)+'\n')
    if accepted:assert capture(output,p)['diagnostics']['provider_input_bound_calls']==1
    else:
        with pytest.raises(ValueError,match='exact input receipt'):capture(output,p)
