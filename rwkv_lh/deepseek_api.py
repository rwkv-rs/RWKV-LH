"""Single documented DeepSeek Chat request contract, shared by online and offline callers."""
from copy import deepcopy
import json
import math
from urllib.parse import urlsplit

BACKEND_PROFILE = 'deepseek-official'
ORIGIN = 'https://api.deepseek.com'
TRANSPORT = 'chat_completions'
_OPTIONS = {'thinking', 'reasoning_effort', 'temperature', 'top_p', 'logprobs', 'top_logprobs', 'user_id'}


def endpoint(base_url=ORIGIN, *, strict=False, models=False):
    """Normalize documented base aliases; never reinterpret an arbitrary proxy URL."""
    url = urlsplit(base_url)
    if (url.scheme != 'https' or url.hostname != 'api.deepseek.com'
            or url.port not in (None, 443) or url.username is not None or url.password is not None
            or url.query or url.fragment or url.path.rstrip('/') not in ('', '/v1', '/beta')):
        raise ValueError('DeepSeek requires its official HTTPS base URL (/, /v1 or /beta)')
    return ORIGIN + ('/models' if models else '/beta/chat/completions' if strict else '/chat/completions')


def request_options(value):
    if not isinstance(value, dict) or set(value) - _OPTIONS:
        raise ValueError('DeepSeek request options contain undocumented or contract-owned fields')
    try:
        result = json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError('DeepSeek request options must be finite JSON') from exc
    effort = result.get('reasoning_effort')
    if 'reasoning_effort' in result and effort not in ('none', 'low', 'high', 'max'):
        raise ValueError('DeepSeek request options require documented reasoning_effort none/low/high/max')
    effort_mode = 'enabled' if effort in ('low', 'high', 'max') else 'disabled'
    thinking = result.get('thinking', {'type': effort_mode})
    if thinking not in ({'type': 'disabled'}, {'type': 'enabled'}):
        raise ValueError('DeepSeek request options require thinking enabled or disabled')
    result['thinking'] = thinking
    if 'reasoning_effort' in result and thinking['type'] != effort_mode:
        raise ValueError('DeepSeek request options: reasoning_effort contradicts thinking')
    for key in ('temperature', 'top_p'):
        if key in result and (type(result[key]) not in (int, float) or not math.isfinite(result[key])
                              or not 0 <= result[key] <= (2 if key == 'temperature' else 1)):
            raise ValueError('DeepSeek request options contain invalid ' + key)
    if result.get('top_p') == 0:
        raise ValueError('DeepSeek request options require top_p greater than zero')
    if thinking['type'] == 'enabled' and 'temperature' in result:
        raise ValueError('DeepSeek request options: temperature has no effect in thinking mode')
    if thinking['type'] == 'disabled' and 'top_p' in result:
        raise ValueError('DeepSeek request options: top_p has no effect in non-thinking mode')
    if 'logprobs' in result and type(result['logprobs']) is not bool:
        raise ValueError('DeepSeek request options require boolean logprobs')
    if 'top_logprobs' in result and (type(result['top_logprobs']) is not int
                                    or not 0 <= result['top_logprobs'] <= 20
                                    or result.get('logprobs') is not True):
        raise ValueError('DeepSeek request options require top_logprobs in 0..20 and logprobs=true')
    if 'user_id' in result:
        import re
        if not isinstance(result['user_id'], str) or not re.fullmatch(r'[a-zA-Z0-9\-_]{1,512}', result['user_id']):
            raise ValueError('DeepSeek request options contain invalid user_id')
    return result


def chat_request(*, base_url=ORIGIN, model, system, user, max_tokens, stream=False,
                 options=None, tool_contract=None):
    """Only Chat Completions: native strict functions or documented JSON Output."""
    url = endpoint(base_url, strict=tool_contract is not None)
    settings = request_options(dict(options or {}))
    if not isinstance(model, str) or not model.strip() or type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError('DeepSeek requires an explicit model and positive output token budget')
    if not isinstance(system, str) or not isinstance(user, str) or type(stream) is not bool:
        raise ValueError('DeepSeek requires text messages and a boolean stream flag')
    body = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'max_tokens': max_tokens, 'stream': stream, **settings}
    if tool_contract is None:
        body['response_format'] = {'type': 'json_object'}
        if 'json' not in system.casefold():
            body['messages'][0]['content'] += '\nReturn one JSON object.'
    else:
        from .strong_structured_output import build_tool_contract, PROTOCOL
        if tool_contract.get('protocol') != PROTOCOL or build_tool_contract(tool_contract['original_definitions']) != tool_contract:
            raise ValueError('strict tool contract differs from current original role definitions')
        if settings['thinking'] != {'type': 'disabled'}:
            raise ValueError('DeepSeek required strict calls require thinking disabled')
        body.update(tools=deepcopy(tool_contract['tools']), tool_choice='required')
        body['messages'][0]['content'] += '\nCall the supplied tools with the original parameters inside the declared params field.'
    return url, body, TRANSPORT
