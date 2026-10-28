"""Convert a native checkpoint using the pinned Transformers-RWKV converter.

Run with the dedicated backend environment. The converter and its chat template
are supplied with explicit hashes; neither arbitrary fallback loaders nor local
weight-layout approximations are used.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile

from rwkv_lh.inference.irwkv_artifact import seal_artifact, verify_vocabulary, artifact_files
from rwkv_lh.inference.uploaded_sources import digest
from rwkv_lh.statetune_core import verify_file
from rwkv_lh.token_budget import VOCAB_PATH


def convert(source, output, *, source_sha256, converter, converter_sha256,
            template_sha256, tokenizer_source, tokenizer_sha256, context_length):
    source = verify_file(source, source_sha256).resolve()
    converter = verify_file(converter, converter_sha256).resolve()
    verify_file(converter.with_name('rwkv_chat_template.jinja'), template_sha256)
    tokenizer_source = verify_file(tokenizer_source, tokenizer_sha256).resolve()
    output = Path(output).absolute()
    if output.exists() or type(context_length) is not int or context_length <= 0:
        raise ValueError('output must be new and context length must be positive')
    spec = importlib.util.spec_from_file_location('rwkv_canonical_converter', converter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.irwkv-convert-', dir=output.parent) as staging:
        staging = Path(staging)
        module.convert_checkpoint(source, staging, context_length, '5GB', tokenizer_source)
        vocabulary = verify_vocabulary(staging, VOCAB_PATH)
        # Reopen every serving tensor and compare the canonical name mapping.
        # The converter only squeezes [1,1,C]; it must never round weights.
        import torch
        from safetensors import safe_open
        original = module.load_checkpoint(source)
        mapping, dropped = module.translation_plan(original)
        seen = set()
        for name in artifact_files(staging):
            if not name.endswith('.safetensors'):
                continue
            with safe_open(staging/name, framework='pt', device='cpu') as shard:
                for key in shard.keys():
                    if key not in mapping or key in seen:
                        raise ValueError('unexpected or duplicate converted tensor: ' + key)
                    actual = shard.get_tensor(key)
                    expected = module.converted_tensor(original[mapping[key]], actual.shape)
                    if actual.dtype != expected.dtype or not torch.equal(actual, expected):
                        raise ValueError('converted tensor values differ: ' + key)
                    seen.add(key)
        if seen != set(mapping) or dropped != set(original).intersection(module.LAYER_ZERO_UNUSED):
            raise ValueError('converted tensor coverage differs')
        audit = dict(compared_tensors=len(seen), excluded_unused_tensors=sorted(dropped), values_changed=False)
        (staging/'conversion_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
        # The manifest binds the final absolute root, after atomic publication.
        os.rename(staging, output)
    return seal_artifact(output, source=dict(path=str(source), sha256=source_sha256),
        converter=dict(path=str(converter), sha256=converter_sha256,
                       chat_template_sha256=template_sha256, tokenizer_source_sha256=tokenizer_sha256),
        source_vocabulary_sha256=vocabulary['source_vocabulary_sha256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','converter','tokenizer-source'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('source-sha256','converter-sha256','template-sha256','tokenizer-sha256'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--context-length', type=int, required=True)
    print(json.dumps(convert(**vars(parser.parse_args())), indent=2))


if __name__ == '__main__':
    main()
