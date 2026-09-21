import json

import pytest

from rwkv_lh.offline_teacher_api import DeepSeekTeacher


def client(tmp_path, **changes):
    key = tmp_path / 'credential'
    key.write_text('test-secret')
    options = dict(directory=tmp_path / 'audit', key_file=key, model='deepseek-flash',
                   budget_usd=1, input_usd_per_million=.3, output_usd_per_million=1.2,
                   max_output_tokens=100, max_requests=2)
    options.update(changes)
    return DeepSeekTeacher(**options)


def transport(monkeypatch, callback):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            return callback(url, kwargs)
    monkeypatch.setattr('rwkv_lh.offline_teacher_api.requests.Session', Session)


def test_reservation_precedes_network_and_credential_not_logged(tmp_path, monkeypatch):
    api = client(tmp_path)
    def post(url, options):
        ledger = json.loads((api.directory / 'LEDGER.json').read_text())
        assert ledger['requests'][0]['status'] == 'reserved'
        assert options['allow_redirects'] is False
        assert options['json']['thinking'] == {'type': 'disabled'}
        class Response:
            status_code = 200
            text = json.dumps({'id': 'provider-1', 'model': 'deepseek-flash',
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
                'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]})
        return Response()
    transport(monkeypatch, post)
    value, identity = api.complete('test', 'input')
    assert value == {'ok': True} and identity['model'] == 'deepseek-flash'
    assert not any('test-secret' in p.read_text() for p in api.directory.glob('*.json'))
    row = json.loads((api.directory / 'LEDGER.json').read_text())['requests'][0]
    assert row['charged_estimate_usd'] == pytest.approx(9e-6)


def test_timeout_keeps_reservation_and_no_retry(tmp_path, monkeypatch):
    api = client(tmp_path, max_requests=1)
    calls = []
    def post(*args):
        calls.append(1)
        raise TimeoutError('test-secret must never enter ledger')
    transport(monkeypatch, post)
    with pytest.raises(TimeoutError):
        api.complete('test', 'input')
    with pytest.raises(ValueError, match='budget'):
        api.complete('test', 'input')
    assert len(calls) == 1
    text = (api.directory / 'LEDGER.json').read_text()
    assert 'test-secret' not in text
    assert json.loads(text)['requests'][0]['charged_estimate_usd'] > 0


def test_budget_rejects_before_network(tmp_path, monkeypatch):
    api = client(tmp_path, budget_usd=1e-9)
    transport(monkeypatch, lambda *a: pytest.fail('must not call provider'))
    with pytest.raises(ValueError, match='budget'):
        api.complete('test', 'input')


@pytest.mark.parametrize('finish,content', [('length', '{"ok":true}'), ('stop', ''), ('stop', '```json\n{}\n```')])
def test_incomplete_or_repaired_json_never_accepted(tmp_path, monkeypatch, finish, content):
    api = client(tmp_path)
    class Response:
        status_code = 200
        text = json.dumps({'usage': {'prompt_tokens': 1, 'completion_tokens': 5},
            'choices': [{'finish_reason': finish, 'message': {'content': content}}]})
    transport(monkeypatch, lambda *a: Response())
    with pytest.raises(ValueError):
        api.complete('test', 'input')
    assert json.loads((api.directory / 'LEDGER.json').read_text())['requests'][0]['status'] == 'failed_or_uncertain'
