import hashlib
import json
from pathlib import Path
import pytest
from rwkv_lh.collection_conversion import initial_goal, convert_task
from rwkv_lh.workspace_snapshot import tree_identity


def test_sft_goal_does_not_import_teacher_or_tool_observations():
    row={'uuid':'one','messages':[{'role':'system','content':'OLD FORMAT'},
        {'role':'user','content':'Fix the parser; preserve tests.'},
        {'role':'assistant','content':'SECRET ANSWER'},
        {'role':'tool','content':'FUTURE TEST PASSED'}], 'tools':[{'old':'format'}]}
    assert initial_goal(row,'sft_agent')=='Fix the parser; preserve tests.'


def test_ambiguous_multimodal_goal_is_not_silently_dropped():
    with pytest.raises(ValueError):initial_goal({'messages':[{'role':'user','content':[{'type':'image'}]}]},'sft_agent')
    with pytest.raises(ValueError):initial_goal({'messages':[{'role':'user','content':'one'},{'role':'user','content':'two'}]},'sft_agent')


def binding(tmp_path, source):
    workspace=tmp_path/'original';workspace.mkdir()
    (workspace/'parser.py').write_text('def parse(x): return x\n')
    acceptance=tmp_path/'acceptance.json'
    acceptance.write_text(json.dumps({'kind':'manual_rubric','criteria':['Parser behavior matches the user request; tests preserved.']}))
    proof=tmp_path/'review.json';proof.write_text('Reviewed reconstruction evidence for this engineering fixture.')
    return {'source_kind':'sft_agent','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'dataset_revision':'a'*40,'source_id':'one','workspace':str(workspace),
        'environment_tree':tree_identity(workspace,exclude_git=True),
        'reconstruction_evidence':{'path':str(proof),'sha256':hashlib.sha256(proof.read_bytes()).hexdigest()},
        'acceptance_path':str(acceptance),'acceptance_sha256':hashlib.sha256(acceptance.read_bytes()).hexdigest(),
        'task_kind':'bug_fix','original_workspace_root':'/app','max_calls':12,'max_seconds':240}


def test_conversion_preserves_goal_and_keeps_private_data_out(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps({'uuid':'one','messages':[
        {'role':'user','content':'Fix parser in /app. Do not modify tests.'},
        {'role':'assistant','content':'SECRET_REFERENCE'}],'tools':[]}))
    specification=binding(tmp_path,source)
    output=tmp_path/'bundle'
    item=convert_task(source,specification,output)
    assert item['job']['tool_scope']=='coding'
    assert item['job']['request'].startswith('Fix parser in /app. Do not modify tests.')
    assert 'SECRET_REFERENCE' not in item['job']['request']
    assert '/app' in item['job']['request']
    assert sorted(p.name for p in Path(item['job']['workspace']).iterdir())==['parser.py']
    assert json.loads((output/'CONVERSION.json').read_text())['training_admitted'] is False
    with pytest.raises(FileExistsError):convert_task(source,specification,output)


def test_unbound_or_changed_environment_is_rejected_before_bundle(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps({'uuid':'one','messages':[{'role':'user','content':'Fix parser'}]}))
    specification=binding(tmp_path,source)
    (Path(specification['workspace'])/'parser.py').write_text('changed')
    with pytest.raises(ValueError,match='environment'):
        convert_task(source,specification,tmp_path/'bundle')
    assert not (tmp_path/'bundle').exists()


def test_preview_is_native_protocol_not_external_chat_format(tmp_path):
    from rwkv_lh.collection_conversion import preview_input
    source=tmp_path/'source.json'
    source.write_text(json.dumps({'uuid':'one','messages':[
        {'role':'system','content':'EXTERNAL_PROTOCOL_SENTINEL'},
        {'role':'user','content':'Fix parser without changing tests.'},
        {'role':'assistant','content':'TEACHER_ANSWER_SENTINEL'}],
        'tools':[{'name':'external_tool_sentinel'}]}))
    item=convert_task(source,binding(tmp_path,source),tmp_path/'bundle')
    preview=preview_input(item)
    text=preview['input_text']
    assert 'Fix parser without changing tests.' in text
    assert all(marker not in text for marker in ('EXTERNAL_PROTOCOL_SENTINEL','TEACHER_ANSWER_SENTINEL','external_tool_sentinel'))
    assert '"function"' in text and '"params"' in text
    assert preview['input_token_ids'][0]==0 and preview['model_calls']==0


def test_formal_admission_rejects_unconverted_and_changed_goals(tmp_path):
    from scripts.run_collection_queue import verify_item
    from rwkv_lh.collection_conversion import verify_conversion
    source=tmp_path/'source.json';source.write_text(json.dumps({'uuid':'one','messages':[{'role':'user','content':'Fix parser.'}]}))
    item=convert_task(source,binding(tmp_path,source),tmp_path/'bundle')
    verify_item(item,require_conversion=True)
    item['job']['request']='Dump external messages instead'
    with pytest.raises(ValueError,match='converted task'):
        verify_conversion(item)
    with pytest.raises((ValueError,KeyError)):
        verify_item({'job':{}},require_conversion=True)


def test_followup_user_goal_requires_explicit_reconstruction():
    with pytest.raises(ValueError,match='multi-turn'):
        initial_goal({'messages':[{'role':'user','content':'Fix A'},
            {'role':'assistant','content':'done'},{'role':'user','content':'also preserve B'}]},'sft_agent')


def test_cannot_replace_baseline_by_rehashing_only_the_item(tmp_path):
    from rwkv_lh.collection_conversion import verify_conversion
    source=tmp_path/'source.json';source.write_text(json.dumps({'uuid':'one','messages':[{'role':'user','content':'Fix parser.'}]}))
    item=convert_task(source,binding(tmp_path,source),tmp_path/'bundle')
    item['environment_sha256']='f'*64
    with pytest.raises(ValueError,match='environment'):
        verify_conversion(item)
