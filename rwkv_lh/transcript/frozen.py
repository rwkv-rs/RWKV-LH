"""Read owner-sealed current transcript tokens; never convert or create a dataset.

The complete manifest is authorized by the training registration. Embedded
owner/audit references bind ``data_digest`` (the manifest's data identity, with
those references excluded), avoiding a circular manifest/authorization hash.
Production provenance is an owner-audited, sealed source manifest; a filename
or a self-declared boolean is never sufficient.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

from ..project_contracts import digest, fields, text
from .parse import loads, parse_transcript, parse_assistant, validate_messages
from .render import PROTOCOL, compact
from .tools import TOOL_PROTOCOL, canonical_definitions
from .tokenize import tokenize_transcript

MANIFEST_SCHEMA = 'rwkv-lh.transcript-token-manifest.v1'
SOURCE_SCHEMA = 'rwkv-lh.transcript-production-sources.v1'
FORMAT = 'transcript_tokens'
PROTOCOL_FILES = ('render.py', 'parse.py', 'tools.py', 'tokenize.py')
IDENTITY_FIELDS = ('schema_version', 'input_protocol', 'tool_protocol', 'model_sha256',
    'tokenizer_sha256', 'protocol_sources', 'generation_script', 'source_manifest', 'splits')


def _sha(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('lowercase SHA-256 identity required')
    return value


def _bytes(reference, base):
    fields(reference, ('path', 'sha256'))
    path = Path(text(reference['path']))
    path = path if path.is_absolute() else base / path
    if path.is_symlink() or not path.is_file():
        raise ValueError('sealed reference must be a regular file')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _sha(reference['sha256']):
        raise ValueError('sealed file SHA-256 differs: ' + str(path))
    return raw, path.resolve()


def _json(reference, base):
    raw, path = _bytes(reference, base)
    return loads(raw), path


def data_digest(manifest):
    """Identity signed by embedded owner evidence; full-manifest SHA stays external."""
    return digest({key: manifest[key] for key in IDENTITY_FIELDS})


def validate_token_row(row, *, vocab_size=None, context_tokens=None):
    fields(row, ('episode_id', 'source', 'input_protocol', 'input_ids', 'loss_mask'))
    text(row['episode_id']); text(row['source'])
    if row['input_protocol'] != PROTOCOL:
        raise ValueError('only current complete transcript tokens are accepted')
    tokens, mask = row['input_ids'], row['loss_mask']
    if (not isinstance(tokens, list) or len(tokens) < 2
            or any(type(token) is not int or token <= 0 for token in tokens)
            or not isinstance(mask, list) or len(mask) != len(tokens)
            or any(type(value) is not int or value not in (0, 1) for value in mask)
            or mask[0] != 0 or not any(mask)):
        raise ValueError('invalid complete transcript input_ids/loss_mask')
    if vocab_size is not None and any(token >= vocab_size for token in tokens):
        raise ValueError('transcript token outside frozen vocabulary')
    if context_tokens is not None and len(tokens) > context_tokens:
        raise ValueError('complete transcript exceeds context capacity; no truncation')
    return deepcopy(row)


def _owner_evidence(manifest, base):
    binding = {'data_digest': manifest['data_digest'],
               'source_manifest_sha256': manifest['source_manifest']['sha256']}
    for key in ('authorization_references', 'audit_references'):
        references = manifest[key]
        if not isinstance(references, list) or not references:
            raise ValueError('sealed owner authorization and audit references are required')
        for reference in references:
            evidence, _ = _json(reference, base)
            if not isinstance(evidence, dict) or any(evidence.get(k) != v for k, v in binding.items()):
                raise ValueError('owner evidence does not bind the exact dataset and production source identities')
            text(evidence.get('owner_instruction'))
            if key == 'audit_references':
                audits = evidence.get('audits')
                if (evidence.get('training_eligible') is not True or not isinstance(audits, dict)
                        or any(not isinstance(audits.get(k), dict) or not audits[k]
                               for k in ('split', 'similarity', 'coverage'))):
                    raise ValueError('eligible split, similarity and coverage audit evidence required')


def _production_sources(manifest, base, native_tools):
    source_manifest, source_path = _json(manifest['source_manifest'], base)
    fields(source_manifest, ('schema_version', 'origin', 'files'))
    if source_manifest['schema_version'] != SOURCE_SCHEMA or source_manifest['origin'] != 'production':
        raise ValueError('owner-audited production source manifest required')
    files = source_manifest['files']
    if not isinstance(files, list) or not files:
        raise ValueError('production transcript source files required')
    expected_tools = canonical_definitions(native_tools)
    sources = {}
    for entry in files:
        fields(entry, ('path', 'sha256', 'input_protocol'))
        if entry['input_protocol'] != PROTOCOL:
            raise ValueError('retired production input protocol cannot be relabelled')
        reference = {key: entry[key] for key in ('path', 'sha256')}
        raw, path = _bytes(reference, source_path.parent)
        if entry['sha256'] in sources:
            raise ValueError('duplicate production source identity')
        document = parse_transcript(raw)
        validate_messages(document['messages'], allow_pending=False)
        if document['tools'] != expected_tools:
            raise ValueError('production source must use the current frozen nine-tool catalog')
        for message in document['messages']:
            if message['role'] == 'assistant':
                parse_assistant(compact(message), native_tools)
        sources[entry['sha256']] = {'path': path}
    return sources


def read_manifest(path, expected_sha256):
    """Reject retired/relabelled formats before any model, source or GPU checks."""
    path = Path(path).absolute()
    manifest, path = _json({'path': str(path), 'sha256': expected_sha256}, path.parent)
    fields(manifest, (*IDENTITY_FIELDS, 'data_digest', 'authorization_references', 'audit_references'))
    if (manifest['schema_version'] != MANIFEST_SCHEMA or manifest['input_protocol'] != PROTOCOL
            or manifest['tool_protocol'] != TOOL_PROTOCOL):
        raise ValueError('only current transcript token manifests are accepted; no legacy conversion')
    if manifest['data_digest'] != data_digest(manifest):
        raise ValueError('frozen transcript data digest differs')
    return manifest


def load_split(path, expected_sha256, split, *, context_tokens, vocab_size,
               model_sha256, tokenizer_sha256, tokenizer, native_tools):
    """Return (manifest, rows), verifying every row before atomic export publication.

    The row iterator verifies its file hash/count at EOF and compares complete
    tokens/masks with the shared transcript codec. It returns the supplied rows
    unchanged; recomputation is validation, never a format conversion.
    """
    if (type(context_tokens) is not int or context_tokens < 2
            or type(vocab_size) is not int or vocab_size < 2):
        raise ValueError('explicit positive context and vocabulary capacities required')
    path = Path(path).absolute()
    manifest = read_manifest(path, expected_sha256)
    if manifest['model_sha256'] != _sha(model_sha256) or manifest['tokenizer_sha256'] != _sha(tokenizer_sha256):
        raise ValueError('frozen model/tokenizer identity differs from the native artifact')
    expected_sources = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in PROTOCOL_FILES}
    if manifest['protocol_sources'] != expected_sources:
        raise ValueError('transcript protocol source SHA-256 differs')
    base = path.parent
    _bytes(manifest['generation_script'], base)
    _owner_evidence(manifest, base)
    sources = _production_sources(manifest, base, native_tools)
    splits = manifest['splits']
    if not isinstance(splits, dict) or split not in splits:
        raise ValueError('requested frozen split is unavailable')
    selected = splits[split]
    fields(selected, ('path', 'sha256', 'rows'))
    if type(selected['rows']) is not int or selected['rows'] < 1:
        raise ValueError('nonempty frozen split row count required')
    split_path = Path(text(selected['path']))
    split_path = split_path if split_path.is_absolute() else base / split_path
    expected_hash = _sha(selected['sha256'])
    if split_path.is_symlink() or not split_path.is_file():
        raise ValueError('frozen split must be a regular file')

    def rows():
        observed, identifiers, count = hashlib.sha256(), set(), 0
        with split_path.open('rb') as stream:
            for line in stream:
                observed.update(line)
                row = validate_token_row(loads(line), vocab_size=vocab_size, context_tokens=context_tokens)
                if row['episode_id'] in identifiers or row['source'] not in sources:
                    raise ValueError('duplicate episode or unknown production source identity')
                identifiers.add(row['episode_id'])
                source = sources[row['source']]
                # Re-read each sealed source when used, so later replacement cannot
                # mix a frozen manifest with different model-visible source bytes.
                document, _ = _json({'path': str(source['path']), 'sha256': row['source']}, base)
                expected = tokenize_transcript(document['messages'], tokenizer=tokenizer, max_tokens=context_tokens)
                if row['input_ids'] != expected['input_ids'] or row['loss_mask'] != expected['loss_mask']:
                    raise ValueError('complete transcript tokens or supervision mask differ from the production source')
                count += 1
                yield row
        if observed.hexdigest() != expected_hash or count != selected['rows']:
            raise ValueError('frozen split SHA-256 or row count differs; no store may be published')
    return manifest, rows()
