"""Offline teacher policy over the product Agent loop and its one native codec."""
import asyncio
import hashlib
import json
import requests
from types import SimpleNamespace
from rwkv_lh.project_protocols import agent
from rwkv_lh.project_runtime import AgentReply
from rwkv_lh.transcript.parse import catalog,validate_assistant
from rwkv_lh.transcript.render import assistant_message,tool_call
from rwkv_lh.transcript.tools import canonical_definitions
from rwkv_lh.transcript.wire import parse_assistant,render_body

TEACHER_FORMAT = (
    'You are an offline teacher generating the next assistant turn of a coding-agent conversation. '
    'The user supplies the exact production conversation as JSON data. Continue that conversation '
    'using the native API function tools provided here. Respect its task, permissions and observed tool results. '
    'Its System describes a target serialization layout; a deterministic codec will render that layout '
    'from your native tool calls, so do not imitate the tags in your output. Do not put XML tool or think '
    'tags in content. Call tools for every action, and call finish_work only when the requested work is done '
    'or actually blocked. Use content only for brief narration. Never claim tests you have not run. '
    'Keep track of the current project, the user\'s requested outcome, what the observed results establish, '
    'and what remains uncertain. Explain the next action and its purpose in your own words when useful. '
    'Revise your plan after contradictory evidence. A failed command is evidence to investigate, not '
    'an instruction to repeat it unchanged. Choose the tools and order the project needs; no fixed stage '
    'sequence or repeated status template is required. Finish with an accurate report of actual results '
    'and remaining limitations, including failures. Do not invent a successful outcome.')


def teacher_messages(payload):
    return [{'role':'system','content':TEACHER_FORMAT},
            {'role':'user','content':json.dumps({'production_messages':payload['messages']},ensure_ascii=False)}]


class TeacherPolicy:
    def __init__(self,pool,loop,*,episode,max_output_tokens=8192):
        self.pool,self.loop,self.episode=pool,loop,episode
        self.max_output_tokens=max_output_tokens

    def complete(self,payload,definitions,key):
        return asyncio.run_coroutine_threadsafe(self.pool.complete(teacher_messages(payload),
            tools=canonical_definitions(definitions),key=key,max_output_tokens=self.max_output_tokens),self.loop).result()

    def request(self,lane,payload,definitions,checkpoint):
        agent.validate_input(payload)
        sequence=len(payload['messages'])
        key=self.episode+':'+hashlib.sha256(json.dumps(payload['messages'],ensure_ascii=False).encode()).hexdigest()
        response=self.complete(payload,definitions,key)
        selected=response['choices'][0];native=selected['message']
        evidence={'teacher_model':self.pool.provider['model'],'teacher_provider':self.pool.provider['id'],
            'offline_only':True,'request_key':key,'usage':response.get('usage'),
            'teacher_transport':'native_api_to_production_codec','teacher_message':native,
            'raw_generation':{'raw_output':json.dumps(native,ensure_ascii=False),'finish_reason':selected.get('finish_reason')}}
        checkpoint={'offline_teacher':self.pool.provider['model'],'messages':payload['messages'],'request_key':key}
        if selected.get('finish_reason')=='length':
            return AgentReply({'function':'model_output_budget_exhausted','params':{}},checkpoint,{**evidence,'known_budget_exhaustion':True})
        try:
            # The codec owns wire serialization; parameter values and narration
            # are never repaired, stripped, or completed by the teacher adapter.
            calls=[tool_call(f'call_{sequence}_{i}',c['function']['name'],json.loads(c['function']['arguments']),definitions)
                   for i,c in enumerate(native.get('tool_calls') or [])]
            message=assistant_message(content=native.get('content'),reasoning_content=native.get('reasoning_content'),tool_calls=calls)
            validate_assistant(message,definitions)
            raw=render_body(message,catalog(definitions))
            parsed=parse_assistant(raw,definitions,id_prefix=f'call_{sequence}')
            if render_body(parsed,catalog(definitions))!=raw:raise ValueError('teacher turn is not canonical wire bytes')
            command={'function':'assistant','params':{'message':parsed}}
            agent.validate_references(payload,command)
            evidence['raw_generation']['raw_output']=raw
        except (ValueError,TypeError,KeyError) as exc:
            return AgentReply({'function':'protocol_rejected','params':{'error':str(exc)}},checkpoint,{**evidence,'rejected':True})
        return AgentReply(command,checkpoint,{**evidence,'rejected':False})


class BrokerPolicy(TeacherPolicy):
    """Process worker port; only the broker holds provider credentials."""
    def __init__(self,broker,provider,*,episode,max_output_tokens=8192):
        super().__init__(SimpleNamespace(provider=provider),None,episode=episode,max_output_tokens=max_output_tokens)
        self.broker=broker

    def complete(self,payload,definitions,key):
        with requests.Session() as session:
            session.trust_env=False
            response=session.post(self.broker['url'],headers={'Authorization':'Bearer '+self.broker['token']},json={'provider':self.pool.provider['id'],
                'messages':teacher_messages(payload),'tools':canonical_definitions(definitions),
                'key':key,'max_output_tokens':self.max_output_tokens},timeout=(10,900))
        value=response.json()
        if response.status_code!=200:raise RuntimeError(value.get('error','teacher broker failed'))
        return value
