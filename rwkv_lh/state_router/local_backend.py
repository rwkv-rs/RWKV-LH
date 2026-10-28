"""Configuration and frozen identities for the irwkv feature worker."""
from dataclasses import dataclass
import json
from pathlib import Path
import re

from rwkv_lh.model_io import canonical_digest
from rwkv_lh.inference.uploaded_sources import ENGINE_SCHEMA, digest, verify_manifest
from rwkv_lh.inference.irwkv_artifact import verify_artifact

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT/'rwkv_lh/inference/irwkv.lock.json').read_text())
_SHA = re.compile('[0-9a-f]{64}')
_PROFILE = re.compile('[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')


@dataclass(frozen=True)
class LocalIRWKVSettings:
    engine_root: Path = Path('/home/chase/GitHub/irwkv')
    engine_revision: str = LOCK['revision']
    engine_python: Path = Path('/home/chase/GitHub/irwkv/.venv/bin/python')
    model: Path = ROOT/'data/models/irwkv'
    batch_size: int = 1
    max_tokens: int = 8192
    wkv_mode: str = 'fp32io16'
    runtime_temp: Path = ROOT/'data/runtime/irwkv'
    state_profile_manifest: Path | None = None
    state_profile_manifest_sha256: str = ''
    state_profile_id: str = ''
    state_profile_sha256: str = ''
    engine_source_manifest: Path | None = None
    engine_source_manifest_sha256: str = ''

    def __post_init__(self):
        for name in ('engine_root','engine_python','model','runtime_temp','state_profile_manifest','engine_source_manifest'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, Path(value).expanduser())
        if not re.fullmatch('[0-9a-f]{40}', self.engine_revision):
            raise ValueError('irwkv revision requires full source commit identity')
        if self.wkv_mode != 'fp32io16' or self.batch_size < 1 or self.max_tokens < 1:
            raise ValueError('irwkv requires FP32 State and positive batch/context limits')
        source = (self.engine_source_manifest is not None, bool(self.engine_source_manifest_sha256))
        if any(source) and not all(source):
            raise ValueError('irwkv source requires manifest and SHA-256')
        profile = (self.state_profile_manifest is not None, bool(self.state_profile_manifest_sha256),
                   bool(self.state_profile_id), bool(self.state_profile_sha256))
        if any(profile) and not all(profile):
            raise ValueError('State profile requires manifest, SHA-256, profile ID and state SHA-256')
        if self.state_profile_id and not _PROFILE.fullmatch(self.state_profile_id):
            raise ValueError('State profile ID is invalid')
        for name in ('state_profile_manifest_sha256','state_profile_sha256','engine_source_manifest_sha256'):
            value = getattr(self, name)
            if value and not _SHA.fullmatch(value):
                raise ValueError(name + ' is invalid')


class LocalIRWKVExtractor:
    def __init__(self, settings=None):
        self.settings = settings or LocalIRWKVSettings()
        self._base_identity = None
        self._last_identity = None

    @property
    def model_hash(self):
        return self._load_base_identity()['model_hash']

    @property
    def feature_dim(self):
        return self._load_base_identity()['hidden_size']

    def identity(self):
        return dict(self._last_identity or self._load_base_identity())

    def _load_base_identity(self):
        if self._base_identity is not None:
            return self._base_identity
        settings = self.settings
        if settings.engine_source_manifest is None:
            raise ValueError('irwkv requires a complete uploaded source manifest')
        engine = verify_manifest(settings.engine_source_manifest, settings.engine_source_manifest_sha256,
            expected_schema=ENGINE_SCHEMA, expected_root=settings.engine_root.resolve(),
            expected_revision=settings.engine_revision,
            required_files=(settings.engine_root.resolve()/'irwkv/model_executor/models/rwkv.py',))
        artifact = verify_artifact(settings.model)
        config = json.loads((settings.model/'config.json').read_text())
        base = dict(backend_version='rwkv-lh.irwkv-features.v1', engine=engine,
            model=str(settings.model.resolve()), model_source=artifact['source'],
            model_manifest_sha256=digest(settings.model/'manifest.json'),
            hidden_size=config['hidden_size'], num_hidden_layers=config['num_hidden_layers'],
            head_size=config['head_size'], vocab_size=config['vocab_size'],
            wkv_mode='fp32io16', runtime_compute_dtype='torch.bfloat16',
            tokenizer_vocab_sha256=artifact['source_vocabulary_sha256'])
        base['model_hash'] = canonical_digest(base)
        self._base_identity = base
        return base
