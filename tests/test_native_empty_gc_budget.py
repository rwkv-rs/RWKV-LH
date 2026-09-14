import json
from contextlib import contextmanager
import pytest
from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal,native_result_digest


def test_empty_gc_work_is_independent_of_historical_state_count(tmp_path,monkeypatch):
    journal=NativeRequestJournal(tmp_path/'journal.sqlite3')
    with journal._connect() as connection:
        rows=[]
        for index in range(5000):
            value={'state_ref':f'retired-{index}','released':True}
            rows.append((value['state_ref'],json.dumps(value),native_result_digest(value),'old-request'))
        connection.executemany('INSERT INTO native_request_states VALUES (?,?,?,?)',rows)
    connect=journal._connect;callbacks=[]
    @contextmanager
    def limited():
        with connect() as connection:
            def progress():
                callbacks.append(1)
                return int(len(callbacks)>20)
            connection.set_progress_handler(progress,50)
            yield connection
    monkeypatch.setattr(journal,'_connect',limited)
    assert journal.reclaimable_store_keys()==[]
    assert len(callbacks)<=20


def test_nonempty_gc_still_rejects_corrupt_state_ownership(tmp_path):
    journal=NativeRequestJournal(tmp_path/'journal.sqlite3')
    with journal._connect() as connection:
        connection.execute('INSERT INTO native_request_states VALUES (?,?,?,?)',('owner',json.dumps({'state_ref':'owner'}),'wrong-digest','old'))
        connection.execute('INSERT INTO native_state_gc VALUES (?)',('a'*64,))
    with pytest.raises(RuntimeError,match='integrity mismatch'):
        journal.reclaimable_store_keys()
