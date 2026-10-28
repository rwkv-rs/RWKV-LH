"""Seal a completed native SkyRL HF export for the irwkv serving loader."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from rwkv_lh.skyrl_training import sealed, sha
from rwkv_lh.inference.irwkv_artifact import (
    REQUIRED, artifact_files, seal_artifact, verify_artifact, verify_vocabulary,
)
from rwkv_lh.token_budget import VOCAB_PATH


def seal_export(export, output, *, prepared_reference, result_reference):
    prepared, result = sealed(prepared_reference), sealed(result_reference)
    run = Path(prepared_reference['path']).resolve().parent
    if (Path(result_reference['path']).resolve().parent != run
            or result.get('trainer') != 'skyrl.train.main_sft'
            or result.get('exit_code') != 0
            or result.get('log_sha256') != sha(run/'skyrl.log')):
        raise ValueError('completed native SkyRL trainer receipt is required')
    export = Path(export).resolve(strict=True)
    export.relative_to(Path(prepared['configuration']['export_path']).resolve(strict=True))
    base = Path(prepared['configuration']['model.path']).resolve(strict=True)
    parent = verify_artifact(base, expected_manifest=prepared['model_manifest'])
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.skyrl-export-', dir=output.parent) as temporary:
        temporary = Path(temporary)
        reused, copied = [], {}
        # Generation policy belongs to deployment; retain the frozen standalone
        # configs instead of Transformers' synthesized model-derived defaults.
        for name in REQUIRED:
            source = export/name
            if name in REQUIRED[4:] or (name != 'config.json' and not source.exists()):
                source = base/name
                reused.append(name)
            if not source.is_file() or source.is_symlink():
                raise ValueError('missing or unsafe export metadata: ' + name)
            shutil.copyfile(source, temporary/name)
            copied[name] = sha(source)
        for source in export.glob('*.safetensors*'):
            if source.is_symlink() or not source.is_file():
                raise ValueError('unsafe export weight file')
            shutil.copyfile(source, temporary/source.name)
            copied[source.name] = sha(source)
        base_config = json.loads((base/'config.json').read_text())
        config = json.loads((temporary/'config.json').read_text())
        for key in ('model_type', 'architectures', 'hidden_size', 'num_hidden_layers',
                    'head_size', 'vocab_size', 'bos_token_id', 'eos_token_id'):
            if config.get(key) != base_config.get(key):
                raise ValueError('export model geometry or tokenizer differs: ' + key)
        verify_vocabulary(temporary, VOCAB_PATH)
        for name in artifact_files(temporary):
            if sha(temporary/name) != copied[name]:
                raise ValueError('export file changed while copying: ' + name)
        os.rename(temporary, output)
    reference = seal_artifact(output, source=result_reference,
        converter=dict(kind='skyrl-native-hf-export', prepared=prepared_reference,
                       parent_manifest=prepared['model_manifest'], reused_metadata=reused),
        source_vocabulary_sha256=parent['source_vocabulary_sha256'])
    return dict(manifest=reference, weights_changed=False, optimizer_steps_inferred=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepared', required=True)
    parser.add_argument('--prepared-sha256', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--result-sha256', required=True)
    args = parser.parse_args()
    result = seal_export(args.export, args.output,
        prepared_reference=dict(path=args.prepared, sha256=args.prepared_sha256),
        result_reference=dict(path=args.result, sha256=args.result_sha256))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
