"""Exercise independently restarted time ledger processes and atomic imports."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def main(workspace):
    workspace = Path(workspace).resolve()
    def run(*arguments, good=True):
        result = subprocess.run([sys.executable, str(workspace/'timebook.py'), *map(str, arguments)], cwd=workspace,
                                capture_output=True, text=True, timeout=25)
        assert (result.returncode == 0) == good, (arguments, result.returncode, result.stderr)
        return json.loads(result.stdout) if good else None
    rng = random.Random(561020)
    anchor = datetime(2028, 2, 28, tzinfo=timezone.utc)
    events = []
    for index in range(73):
        start = anchor + timedelta(seconds=rng.randrange(3*86400))
        end = start + timedelta(seconds=rng.randrange(1, 110000))
        offset = timezone(timedelta(hours=rng.choice([-5, 0, 8])))
        events.append({'id': f't-{index}', 'project': rng.choice(['research', '开发', 'client alpha']),
                       'start': start.astimezone(offset).isoformat(), 'end': end.astimezone(offset).isoformat()})
    events.append({'id': 'midnight', 'project': 'boundary', 'start': '2028-02-28T23:50:00Z', 'end': '2028-02-29T00:20:00Z'})
    def expected(begin, finish):
        begin = datetime.fromisoformat(begin).replace(tzinfo=timezone.utc)
        finish = datetime.fromisoformat(finish).replace(tzinfo=timezone.utc)
        rows = []
        current = begin
        while current < finish:
            projects = {}
            for item in events:
                start = datetime.fromisoformat(item['start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(item['end'].replace('Z', '+00:00'))
                seconds = int((min(end, current+timedelta(days=1)) - max(start, current)).total_seconds())
                if seconds > 0:
                    projects[item['project']] = projects.get(item['project'], 0)+seconds
            if projects:
                rows.append({'date': current.date().isoformat(), 'projects': projects, 'total_seconds': sum(projects.values())})
            current += timedelta(days=1)
        return {'days': rows, 'total_seconds': sum(row['total_seconds'] for row in rows)}
    with tempfile.TemporaryDirectory(prefix='timebook-private-') as raw:
        root = Path(raw)
        database = root/'ledger.sqlite'
        input_file = root/'events.json'
        input_file.write_text(json.dumps(events, ensure_ascii=False))
        assert run('import', database, input_file) == {'inserted': len(events), 'duplicates': 0}
        assert run('import', database, input_file) == {'inserted': 0, 'duplicates': len(events)}
        for begin, finish in [('2028-02-28','2028-03-04'), ('2028-02-29','2028-03-01'), ('2028-03-10','2028-03-11')]:
            assert run('stats', database, '--from', begin, '--to', finish) == expected(begin, finish)
        duplicate = events[0]
        args = [part for key in ('id','project','start','end') for part in ('--'+key, duplicate[key])]
        assert run('add', database, *args) == {'inserted': 0, 'duplicates': 1}
        conflict = dict(events[1], project='changed project')
        input_file.write_text(json.dumps([dict(events[0], id='new-before-conflict'), conflict]))
        run('import', database, input_file, good=False)
        assert run('stats', database, '--from', '2028-02-28', '--to', '2028-03-04') == expected('2028-02-28','2028-03-04')
        invalid = dict(events[0], id='bad-time', end=events[0]['start'])
        input_file.write_text(json.dumps([dict(events[0], id='before-invalid'), invalid]))
        run('import', database, input_file, good=False)
        input_file.write_text(json.dumps([dict(events[0], id='naive', start='2028-02-28T12:00:00')]))
        run('import', database, input_file, good=False)
        assert run('stats', database, '--from', '2028-02-28', '--to', '2028-03-04') == expected('2028-02-28','2028-03-04')
        run('stats', database, '--from', '2028-03-01', '--to', '2028-02-28', good=False)
    print('timebook black-box acceptance passed')


if __name__ == '__main__':
    main(sys.argv[1])
