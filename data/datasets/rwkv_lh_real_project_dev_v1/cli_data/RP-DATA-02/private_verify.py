"""Black-box incremental JSONL acceptance with restarts and malformed records."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def main(workspace):
    workspace = Path(workspace).resolve()
    rng = random.Random(331071)
    start = datetime(2029,7,1,tzinfo=timezone.utc)
    events = [{'id':f'event-{index}', 'timestamp':(start+timedelta(seconds=rng.randrange(3*86400))).isoformat(),
               'path':rng.choice(['/api/users','/api/orders','/health','/资源']), 'status':rng.choice([200,201,301,404,500,503]),
               'bytes':rng.randrange(0,50000)} for index in range(99)]
    events.extend([{'id':'at-start','timestamp':'2029-07-02T00:00:00+00:00','path':'/api/edge','status':500,'bytes':0},
                   {'id':'at-end','timestamp':'2029-07-03T00:00:00+00:00','path':'/api/edge','status':500,'bytes':17}])
    encode = lambda row: (json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    def run(*arguments, good=True):
        result = subprocess.run([sys.executable,str(workspace/'accesslog.py'),*map(str,arguments)], cwd=workspace,
                                capture_output=True,text=True,timeout=30)
        assert (result.returncode == 0) == good, (arguments,result.returncode,result.stderr)
        return json.loads(result.stdout) if good else None
    def expected(begin,finish,minimum=100,prefix='/'):
        low,high = datetime.fromisoformat(begin.replace('Z','+00:00')),datetime.fromisoformat(finish.replace('Z','+00:00'))
        output = {'count':0,'bytes':0,'by_status':{},'by_path':{}}
        for row in events:
            when = datetime.fromisoformat(row['timestamp'])
            if not low <= when < high or row['status'] < minimum or not row['path'].startswith(prefix):
                continue
            output['count'] += 1
            output['bytes'] += row['bytes']
            key = str(row['status'])
            output['by_status'][key] = output['by_status'].get(key,0)+1
            group = output['by_path'].setdefault(row['path'],{'count':0,'bytes':0})
            group['count'] += 1
            group['bytes'] += row['bytes']
        return output
    with tempfile.TemporaryDirectory(prefix='accesslog-private-') as raw:
        root = Path(raw)
        database, source = root/'events.sqlite',root/'access.jsonl'
        prefix = b''.join(encode(row) for row in events[:43])
        partial = encode(events[43])
        cut = len(partial)//2
        source.write_bytes(prefix+partial[:cut])
        assert run('ingest',database,source) == {'inserted':43,'duplicates':0,'rejected':0,'offset':len(prefix)}
        assert run('ingest',database,source) == {'inserted':0,'duplicates':0,'rejected':0,'offset':len(prefix)}
        continuation = partial[cut:] + b''.join(encode(row) for row in events[44:])
        bad_lines = [b'{not json}\n', encode(dict(events[0],id='bad-bytes',bytes=-1)), encode(dict(events[0],bytes=events[0]['bytes']+1))]
        tail = encode(events[0])+b''.join(bad_lines)
        with source.open('ab') as stream:
            stream.write(continuation+tail)
        final_bytes = source.read_bytes()
        assert run('ingest',database,source) == {'inserted':len(events)-43,'duplicates':1,'rejected':3,'offset':len(final_bytes)}
        assert run('ingest',database,source) == {'inserted':0,'duplicates':0,'rejected':0,'offset':len(final_bytes)}
        for begin,finish,minimum,route in [('2029-07-01T00:00:00Z','2029-07-04T00:00:00Z',100,'/'),
                                          ('2029-07-02T00:00:00Z','2029-07-03T00:00:00Z',400,'/api'),
                                          ('2029-08-01T00:00:00Z','2029-08-02T00:00:00Z',100,'/')]:
            assert run('query',database,'--from',begin,'--to',finish,'--status-min',minimum,'--prefix',route) == expected(begin,finish,minimum,route)
        rejected = run('rejections',database)
        first_bad = len(final_bytes)-sum(map(len,bad_lines))
        offsets = [first_bad,first_bad+len(bad_lines[0]),first_bad+len(bad_lines[0])+len(bad_lines[1])]
        assert rejected == {'rejected':3,'rows':[{'source':str(source.resolve()),'offset':offset,'reason':reason}
                            for offset,reason in zip(offsets,['invalid_json','invalid_event','conflicting_id'])]}
        alternate = root/'other.jsonl'
        alternate.write_bytes(encode(events[0]))
        assert run('ingest',database,alternate) == {'inserted':0,'duplicates':1,'rejected':0,'offset':alternate.stat().st_size}
        source.write_bytes(b'['+final_bytes[1:])
        run('ingest',database,source,good=False)
        source.write_bytes(final_bytes[:20])
        run('ingest',database,source,good=False)
        assert run('query',database,'--from','2029-07-01T00:00:00Z','--to','2029-07-04T00:00:00Z') == expected('2029-07-01T00:00:00Z','2029-07-04T00:00:00Z')
        source.write_bytes(final_bytes)
        assert run('ingest',database,source) == {'inserted':0,'duplicates':0,'rejected':0,'offset':len(final_bytes)}
    print('accesslog black-box acceptance passed')


if __name__ == '__main__':
    main(sys.argv[1])
