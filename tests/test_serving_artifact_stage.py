import hashlib
import json
import pytest
from scripts.stage_rwkv_serving_artifact import stage


def test_serving_stage_excludes_audit_weights_and_verifies_content(tmp_path):
    source=tmp_path/'source';source.mkdir()
    keys={'model.safetensors':'weights_sha256','config.json':'config_sha256','rwkv_vocab_v20230424.txt':'vocab_sha256'}
    output={}
    for name,key in keys.items():
        (source/name).write_text(name)
        output[key]=hashlib.sha256(name.encode()).hexdigest()
    for name in ['tokenizer_config.json','special_tokens_map.json']:(source/name).write_text('{}')
    (source/'native_unused_layer0_value_mix.safetensors').write_text('backup is not a serving shard')
    (source/'manifest.json').write_text(json.dumps({'source':{'sha256':'a'*64},'output':output}))
    destination=tmp_path/'serving'
    result=stage(source,destination)
    assert [p.name for p in destination.glob('*.safetensors')]==['model.safetensors']
    assert (destination/'model.safetensors').stat().st_ino==(source/'model.safetensors').stat().st_ino
    assert result['weights_changed'] is False
    (source/'config.json').write_text('tampered')
    with pytest.raises(ValueError,match='checksum'):
        stage(source,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
