"""Stage only serving files from a verified artifact; never glob audit sidecars."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def stage(source, output):
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or source in output.parents or output in source.parents:
        raise ValueError('serving output exists or overlaps source')
    manifest=json.loads((source/'manifest.json').read_text())
    checks={'model.safetensors':'weights_sha256','config.json':'config_sha256',
            'rwkv_vocab_v20230424.txt':'vocab_sha256'}
    for name,key in checks.items():
        if sha(source/name)!=manifest['output'][key]:
            raise ValueError('artifact checksum differs: '+name)
    names=[*checks,'tokenizer_config.json','special_tokens_map.json']
    for name in names:
        if not (source/name).is_file() or (source/name).is_symlink():
            raise ValueError('missing or unsafe serving file: '+name)
    output.mkdir(parents=True)
    for name in names:
        # Hardlink preserves original bytes without duplicating multi-GB weights.
        # The serving loader only reads these files.
        if name=='model.safetensors':os.link(source/name,output/name)
        else:shutil.copyfile(source/name,output/name)
    result={'source_manifest':{'path':str(source/'manifest.json'),'sha256':sha(source/'manifest.json')},
            'source_model_sha256':manifest['source']['sha256'],
            'files':{name:sha(output/name) for name in names},'weights_changed':False,
            'excluded_from_serving':['native_unused_layer0_value_mix.safetensors']}
    (output.parent/(output.name+'.IDENTITY.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(stage(args.source,args.output),indent=2))

if __name__=='__main__':main()
