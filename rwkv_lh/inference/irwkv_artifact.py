"""One sealed Transformers artifact shared by SkyRL training and irwkv."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

SCHEMA = 'rwkv-lh.irwkv-artifact.v1'
REQUIRED = ('config.json', 'tokenizer.json', 'tokenizer_config.json',
            'chat_template.jinja', 'generation_config.json',
            'fake_think_generation_config.json', 'tools_generation_config.json')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def artifact_files(root):
    root = Path(root).resolve(strict=True)
    names = set(REQUIRED)
    index = root / 'model.safetensors.index.json'
    if index.is_file():
        value = json.loads(index.read_text())
        mapping = value.get('weight_map')
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError('invalid model shard index')
        names.add(index.name)
        if any(not isinstance(k, str) or not isinstance(v, str) or not v.endswith('.safetensors')
               for k, v in mapping.items()):
            raise ValueError('invalid model shard identity')
        names.update(mapping.values())
    else:
        names.add('model.safetensors')
    if {p.name for p in root.glob('*.safetensors')} != {n for n in names if n.endswith('.safetensors')}:
        raise ValueError('unregistered weight files in artifact')
    for name in names:
        if (not isinstance(name, str) or PurePosixPath(name).name != name
                or name in ('.', '..') or '\\' in name):
            raise ValueError('artifact paths must be local file names')
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('missing or unsafe artifact file: ' + name)
    return sorted(names)


def verify_config(root):
    config = json.loads((root / 'config.json').read_text())
    if config.get('model_type') != 'rwkv' or config.get('architectures') != ['RwkvForCausalLM']:
        raise ValueError('requires canonical transformers-rwkv model_type=rwkv')
    if config.get('tie_word_embeddings', False):
        raise ValueError('RWKV input and output weights must remain separate')
    for name in REQUIRED[4:]:
        generation = json.loads((root / name).read_text())
        if generation.get('_from_model_config', False):
            raise ValueError('generation configs must be standalone')
    return config


def verify_vocabulary(root, vocabulary):
    """Compare every token ID as bytes, including non-UTF8 vocabulary entries."""
    from rwkv_lh.tokenizer import RWKVTokenizer
    raw = json.loads((Path(root)/'tokenizer.json').read_text())
    model = raw.get('model', {})
    if model.get('type') != 'RwkvTrie' or not isinstance(model.get('vocab'), dict):
        raise ValueError('requires canonical RwkvTrie tokenizer')
    if model['vocab'].get('<|endoftext|>') != 0:
        raise ValueError('missing canonical BOS/EOS token')
    direct = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    encoded = dict(zip(direct, direct))
    for byte in range(256):
        if byte not in encoded:
            encoded[byte] = 256 + len(encoded) - len(direct)
    decode = {chr(character): byte for byte, character in encoded.items()}
    expected = RWKVTokenizer(vocabulary).idx2token
    actual, seen = {}, set()
    for token, index in model['vocab'].items():
        if type(index) is not int or index in seen:
            raise ValueError('duplicate or invalid tokenizer ID')
        seen.add(index)
        if index == 0:
            if token != '<|endoftext|>':
                raise ValueError('invalid BOS/EOS token')
            continue
        try:
            actual[index] = bytes(decode[c] for c in token)
        except KeyError as error:
            raise ValueError('invalid byte-level tokenizer symbol') from error
    if actual != expected:
        raise ValueError('model and production vocabulary token IDs differ')
    return dict(token_count=len(expected), source_vocabulary_sha256=digest(Path(vocabulary)))


def seal_artifact(root, *, source, converter, source_vocabulary_sha256):
    root = Path(root).resolve(strict=True)
    target = root / 'manifest.json'
    if target.exists():
        raise FileExistsError(target)
    verify_config(root)
    names = artifact_files(root)
    result = dict(schema_version=SCHEMA, root=str(root), source=source, converter=converter,
                  source_vocabulary_sha256=source_vocabulary_sha256,
                  files={name:dict(sha256=digest(root/name), bytes=(root/name).stat().st_size) for name in names})
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return dict(path=str(target), sha256=digest(target))


def verify_artifact(root, *, expected_manifest=None):
    root = Path(root).resolve(strict=True)
    path = root / 'manifest.json'
    if expected_manifest is not None:
        if Path(expected_manifest['path']).resolve() != path or digest(path) != expected_manifest['sha256']:
            raise ValueError('artifact manifest identity differs')
    manifest = json.loads(path.read_text())
    if manifest.get('schema_version') != SCHEMA or Path(manifest['root']).resolve() != root:
        raise ValueError('artifact identity or root differs')
    verify_config(root)
    names = artifact_files(root)
    if set(names) != set(manifest['files']):
        raise ValueError('artifact file set differs')
    for name in names:
        path = root/name
        if manifest['files'][name] != dict(sha256=digest(path), bytes=path.stat().st_size):
            raise ValueError('artifact file changed: ' + name)
    return manifest
