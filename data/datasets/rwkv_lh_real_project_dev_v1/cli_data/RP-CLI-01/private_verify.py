"""Black-box backup verification; generated fixtures are private to this run."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import zipfile


def main(workspace):
    workspace = Path(workspace).resolve()
    def run(*arguments, good=True):
        result = subprocess.run([sys.executable, str(workspace/'backup.py'), *map(str, arguments)],
                                cwd=workspace, capture_output=True, text=True, timeout=30)
        assert (result.returncode == 0) == good, (arguments, result.returncode, result.stderr)
        if good:
            return json.loads(result.stdout)
        assert result.stderr.strip(), 'failure needs a diagnostic'
    with tempfile.TemporaryDirectory(prefix='backup-private-') as raw:
        root = Path(raw)
        source = root/'source'
        source.mkdir()
        rng = random.Random(721809)
        expected = {'.hidden': b'hidden\x00bytes', 'nested/unicode-数据.bin': bytes(rng.randrange(256) for _ in range(257))}
        for index in range(17):
            expected[f'group-{index%3}/file-{index}.dat'] = bytes(rng.randrange(256) for _ in range(index*11))
        for name, data in expected.items():
            path = source/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (source/'empty/child').mkdir(parents=True)
        archive = root/'archive.zip'
        assert run('snapshot', source, archive) == {'files': len(expected), 'bytes': sum(map(len, expected.values()))}
        (source/'.hidden').write_bytes(b'changed after backup')
        destination = root/'restored'
        destination.mkdir()
        (destination/'old').write_text('replaced only after validation')
        run('restore', archive, destination)
        actual = {path.relative_to(destination).as_posix(): path.read_bytes() for path in destination.rglob('*') if path.is_file()}
        assert actual == expected
        assert (destination/'empty/child').is_dir()
        pristine = archive.read_bytes()
        (source/'link').symlink_to(source/'.hidden')
        run('snapshot', source, archive, good=False)
        assert archive.read_bytes() == pristine, 'failed snapshot overwrote prior backup'
        (source/'link').unlink()
        corrupt = root/'corrupt.zip'
        with zipfile.ZipFile(archive) as old, zipfile.ZipFile(corrupt, 'w') as new:
            for name in old.namelist():
                new.writestr(name, b'wrong' if name == 'files/.hidden' else old.read(name))
        run('restore', corrupt, destination, good=False)
        assert {path.relative_to(destination).as_posix(): path.read_bytes() for path in destination.rglob('*') if path.is_file()} == expected
        malicious = root/'malicious.zip'
        data = b'escaped'
        manifest = {'version': 1, 'directories': [], 'files': [{'path': '../escaped.txt', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}
        with zipfile.ZipFile(malicious, 'w') as bundle:
            bundle.writestr('manifest.json', json.dumps(manifest))
            bundle.writestr('files/../escaped.txt', data)
        run('restore', malicious, destination, good=False)
        assert not (root/'escaped.txt').exists(), 'archive escaped destination'
        assert (destination/'.hidden').read_bytes() == expected['.hidden']
        empty = root/'empty-source'
        empty.mkdir()
        run('snapshot', empty, root/'empty.zip')
        assert run('restore', root/'empty.zip', root/'empty-output') == {'files': 0, 'bytes': 0}
    print('backup black-box acceptance passed')


if __name__ == '__main__':
    main(sys.argv[1])
