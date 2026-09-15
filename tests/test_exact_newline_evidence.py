import hashlib
import pytest
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.schema import TaskAction


@pytest.mark.parametrize('raw', [b'a\r\nb\n', b'a\rb\r', '首行\r\n次行\n'.encode()])
def test_read_file_keeps_actual_source_bytes(tmp_path, raw):
    (tmp_path/'sample.txt').write_bytes(raw)
    goal = LongHorizonModel.create_literal_goal('Read', str(tmp_path))
    result = ActionHarness().execute(TaskAction('read_file', {'path':'sample.txt'}), goal)
    assert result.success
    assert result.output.encode() == raw
    assert result.metadata['chunk']['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert result.metadata['source_size_bytes'] == len(raw)


def test_bind_evidence_uses_original_crlf_offsets(tmp_path):
    raw=b'first\r\nsecond\r\n'
    (tmp_path/'sample.txt').write_bytes(raw)
    goal=LongHorizonModel.create_literal_goal('Read',str(tmp_path))
    result=ActionHarness()._bind_evidence(goal, {'path':'sample.txt','start_line':2,'end_line':2})
    e=result.evidence[0]
    assert e['start_byte']==7
    assert e['snapshot_sha256']==hashlib.sha256(raw).hexdigest()
    assert raw[e['start_byte']:e['end_byte']].decode()==e['quote']


def test_read_json_error_byte_offset_keeps_crlf(tmp_path):
    raw=b'{\r\n"a": nope\r\n}'
    (tmp_path/'sample.json').write_bytes(raw)
    goal=LongHorizonModel.create_literal_goal('Read',str(tmp_path))
    result=ActionHarness().execute(TaskAction('read_json',{'path':'sample.json'}),goal)
    import json
    assert result.success  # Structured parse diagnostics are successful reads.
    error=json.loads(result.output)['parse_error']
    assert error['byte_offset']==raw.index(b'nope')


def test_replace_text_preserves_unmodified_crlf_bytes(tmp_path):
    raw=b'first\r\nsecond\r\n'
    p=tmp_path/'sample.txt';p.write_bytes(raw)
    goal=LongHorizonModel.create_literal_goal('Edit',str(tmp_path))
    ActionHarness()._replace_text(goal,{'path':'sample.txt','old':'second','new':'changed','base_sha256':hashlib.sha256(raw).hexdigest()})
    assert p.read_bytes()==b'first\r\nchanged\r\n'


def test_remove_line_preserves_other_line_terminators(tmp_path):
    raw=b'first\r\nsecond\r\n'
    p=tmp_path/'sample.txt';p.write_bytes(raw)
    goal=LongHorizonModel.create_literal_goal('Edit',str(tmp_path))
    ActionHarness()._remove_line(goal,{'path':'sample.txt','text':'second','base_sha256':hashlib.sha256(raw).hexdigest()})
    assert p.read_bytes()==b'first\r\n'
