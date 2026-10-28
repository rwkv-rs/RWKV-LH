"""Stage the exact serving files from a sealed canonical irwkv artifact."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from rwkv_lh.inference.irwkv_artifact import verify_artifact, seal_artifact
from rwkv_lh.inference.uploaded_sources import digest


def stage(source, output):
    source=Path(source).resolve(strict=True)
    output=Path(output).absolute()
    if output.exists() or source in output.parents or output in source.parents:
        raise ValueError('serving output exists or overlaps source')
    manifest=verify_artifact(source)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.irwkv-stage-',dir=output.parent) as work:
        work=Path(work)
        for name in manifest['files']:
            # Copy-on-write reflinks are platform dependent. A separate copy
            # prevents accidental edits of the serving tree mutating its source.
            shutil.copyfile(source/name,work/name)
            if digest(work/name)!=manifest['files'][name]['sha256']:
                raise ValueError('source artifact changed during staging')
        os.rename(work,output)
    reference=seal_artifact(output,source=manifest['source'],converter=manifest['converter'],
        source_vocabulary_sha256=manifest['source_vocabulary_sha256'])
    return dict(manifest=reference,source_manifest=dict(path=str(source/'manifest.json'),
        sha256=digest(source/'manifest.json')),weights_changed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(stage(args.source,args.output),indent=2))

if __name__=='__main__':main()
