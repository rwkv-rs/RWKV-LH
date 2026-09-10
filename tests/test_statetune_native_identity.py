import hashlib
import json

import pytest

from rwkv_lh.statetune_native_runtime import verify_project_source
from rwkv_lh.inference.uploaded_sources import PROJECT_SCHEMA


def test_native_source_admission_binds_complete_current_tree(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    code = root / 'model.py'
    code.write_text('value = 1\n')
    manifest = tmp_path / 'source.json'
    manifest.write_text(json.dumps({'schema_version': PROJECT_SCHEMA,
        'project_root': str(root), 'source_root': '.', 'files': [{'path': 'model.py', 'bytes': code.stat().st_size,
        'sha256': hashlib.sha256(code.read_bytes()).hexdigest()}]}))
    ref = {'path': str(manifest), 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    verify_project_source(ref, root)
    extra = root / 'unregistered.py'
    extra.write_text('pass\n')
    with pytest.raises(ValueError, match='source'):
        verify_project_source(ref, root)
    extra.unlink()
    code.write_text('value = 2\n')
    with pytest.raises(ValueError, match='source'):
        verify_project_source(ref, root)


def test_training_rejects_the_replaced_manifest_schema(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    manifest = tmp_path / 'source.json'
    manifest.write_text(json.dumps({'schema_version':'rwkv-lh.uploaded-project-source.v1',
        'remote_root':str(root),'files':[]}))
    ref = {'path':str(manifest),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
    with pytest.raises(ValueError,match='source'):
        verify_project_source(ref,root)
