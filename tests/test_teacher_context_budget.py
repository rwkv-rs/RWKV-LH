from unittest.mock import Mock
import pytest
from rwkv_lh.teacher_runtime import ContextCheckedTeacherClient
from rwkv_lh.read_only_agent import ReadOnlyBudgetExpired
from rwkv_lh.supervisor_openai import SupervisorAPISettings


def test_teacher_checks_actual_chat_tokens_before_generation():
    settings = SupervisorAPISettings(base_url='http://localhost:18244/v1',api_key='',model='test',stage_checker_model='test')
    client = ContextCheckedTeacherClient(settings, max_context_tokens=32768)
    reply = Mock();reply.json.return_value={'count':24577, 'tokens':list(range(24577))}
    session=Mock();session.post.return_value=reply
    client._session=lambda:session
    with pytest.raises(ReadOnlyBudgetExpired,match='context'):
        client._post_completion(settings.base_url+'/chat/completions',
            {'model':'test','messages':[{'role':'user','content':'task'}], 'max_tokens':8192}, audit_context={})
    assert session.post.call_count==1
    assert session.post.call_args.args[0]=='http://localhost:18244/tokenize'
    client.close()


def test_teacher_reasoning_only_length_stop_is_task_budget_not_service_failure(tmp_path):
    from rwkv_lh.strong_session import StrongCompletion
    settings = SupervisorAPISettings(base_url='http://localhost:18244/v1',api_key='',model='test',stage_checker_model='test')
    client = StrongCompletion(settings, tmp_path, 1)
    def response(**kwargs):
        client.audit({'type':'supervisor_response_envelope_received','raw_response':{
            'choices':[{'finish_reason':'length','message':{'content':None,'reasoning_content':'unfinished'}}]}})
    client.client._request_json = response
    with pytest.raises(ReadOnlyBudgetExpired,match='output budget'):
        client.text_completion('source input')
    client.client.close()
