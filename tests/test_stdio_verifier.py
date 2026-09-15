"""Black-box stdio checking never mounts private cases in the submission sandbox."""
import pytest


def verify(tmp_path, code, inputs=('3\n',), outputs=('6\n',), **kwargs):
    from rwkv_lh.stdio_verifier import verify_python_submission
    workspace = tmp_path / 'submission'
    workspace.mkdir(exist_ok=True)
    (workspace / 'solution.py').write_text(code)
    return verify_python_submission(workspace, {'call_type': 'std', 'fn_name': None,
        'inputs': list(inputs), 'outputs': list(outputs)}, **kwargs)


def test_correct_submission_and_trailing_whitespace(tmp_path):
    r = verify(tmp_path, 'print(int(input())*2)\n', outputs=('6  \n',))
    assert r['passed'] and r['cases'][0]['exit_code'] == 0


def test_incorrect_answer_and_crash_are_not_success(tmp_path):
    assert not verify(tmp_path, 'print(7)')['passed']
    r = verify(tmp_path, 'raise RuntimeError("bad")')
    assert not r['passed'] and r['cases'][0]['exit_code'] != 0


@pytest.mark.parametrize('inputs,outputs', [((), ()), (('1',), ()), (('1',), ('1','2'))])
def test_invalid_ground_truth_is_rejected(tmp_path, inputs, outputs):
    with pytest.raises(ValueError):
        verify(tmp_path, 'print(1)', inputs, outputs)


def test_timeout_is_recorded_and_original_submission_unchanged(tmp_path):
    code = 'while True: pass\n'
    r = verify(tmp_path, code, timeout_seconds=.2)
    assert not r['passed'] and r['cases'][0]['termination'] == 'timeout'
    assert (tmp_path/'submission/solution.py').read_text() == code


def test_hidden_files_are_not_mounted(tmp_path):
    hidden = tmp_path/'private-answer.txt'
    hidden.write_text('SECRET')
    code = f'from pathlib import Path\nprint(Path({str(hidden)!r}).exists())\n'
    assert verify(tmp_path, code, outputs=('False',))['passed']


def test_output_flood_is_bounded(tmp_path):
    r = verify(tmp_path, 'import os\nwhile True: os.write(1,b"x"*65536)\n', max_output_bytes=4096)
    assert not r['passed']
    assert len(r['cases'][0]['stdout'].encode()) <= 4096


def test_each_case_uses_fresh_workspace(tmp_path):
    code = 'from pathlib import Path\np=Path("marker")\nprint(p.exists())\np.touch()\n'
    assert verify(tmp_path, code, inputs=('',''), outputs=('False','False'))['passed']
