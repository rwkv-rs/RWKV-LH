"""Transactional portable backup and restore CLI."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('invalid relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or value != path.as_posix() or value == '.':
        raise ValueError('unsafe relative path')
    return path


def snapshot(source, archive):
    source, archive = Path(source).resolve(), Path(archive).absolute()
    if not source.is_dir() or archive.resolve().is_relative_to(source):
        raise ValueError('source must be a directory and archive must be outside source')
    archive.parent.mkdir(parents=True, exist_ok=True)
    files, directories = [], []
    for path in sorted(source.rglob('*')):
        if path.is_symlink():
            raise ValueError('symbolic links are unsupported')
        relative = path.relative_to(source).as_posix()
        safe_relative(relative)
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            data = path.read_bytes()
            files.append((relative, data))
        else:
            raise ValueError('only regular files and directories are supported')
    manifest = {'version': 1, 'directories': directories, 'files': [
        {'path': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for name, data in files]}
    handle, temporary = tempfile.mkstemp(prefix='.backup-', dir=archive.parent)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as output:
            output.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
            for name, data in files:
                output.writestr('files/' + name, data)
        os.replace(temporary, archive)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {'files': len(files), 'bytes': sum(len(data) for _, data in files)}


def restore(archive, destination):
    destination = Path(destination).absolute()
    if destination.is_symlink() or destination == destination.parent:
        raise ValueError('invalid destination')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.restore-', dir=destination.parent))
    previous = None
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if len(set(names)) != len(names):
                raise ValueError('duplicate archive member')
            manifest = json.loads(bundle.read('manifest.json'))
            if manifest.get('version') != 1:
                raise ValueError('unsupported manifest version')
            files, directories = manifest['files'], manifest['directories']
            declared = [record['path'] for record in files]
            if len(set(declared)) != len(declared) or len(set(directories)) != len(directories):
                raise ValueError('duplicate manifest path')
            if set(names) != {'manifest.json', *('files/' + name for name in declared)}:
                raise ValueError('undeclared archive member')
            for directory in directories:
                (stage / safe_relative(directory)).mkdir(parents=True, exist_ok=True)
            byte_count = 0
            for record in files:
                name = record['path']
                target = stage / safe_relative(name)
                data = bundle.read('files/' + name)
                if record['size'] != len(data) or record['sha256'] != hashlib.sha256(data).hexdigest():
                    raise ValueError('file integrity mismatch')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                byte_count += len(data)
        if destination.exists():
            if not destination.is_dir():
                raise ValueError('destination must be a directory')
            previous = Path(tempfile.mkdtemp(prefix='.previous-', dir=destination.parent))
            previous.rmdir()
            os.replace(destination, previous)
        try:
            os.replace(stage, destination)
        except BaseException:
            if previous is not None:
                os.replace(previous, destination)
                previous = None
            raise
        if previous is not None:
            shutil.rmtree(previous)
        return {'files': len(files), 'bytes': byte_count}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('snapshot', 'restore'):
        command = commands.add_parser(name)
        command.add_argument('source')
        command.add_argument('destination')
    args = parser.parse_args()
    try:
        value = snapshot(args.source, args.destination) if args.command == 'snapshot' else restore(args.source, args.destination)
        print(json.dumps(value, sort_keys=True))
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
