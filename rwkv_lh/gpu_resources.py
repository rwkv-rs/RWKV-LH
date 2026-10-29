"""Resolve explicit physical GPUs and refuse occupied devices before execution."""
import csv
import re
import subprocess

_UUID = re.compile(r'GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')


def gpu_uuid(index):
    if type(index) is not int or index < 0:
        raise ValueError('GPU index must be a nonnegative integer')
    value = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid',
        '--format=csv,noheader', '-i', str(index)], text=True).strip()
    if not _UUID.fullmatch(value):
        raise ValueError('nvidia-smi did not return one physical GPU UUID')
    return value


def require_idle_gpu(device):
    """Return the observed card and process snapshot; never modify other jobs."""
    if not isinstance(device, str) or not _UUID.fullmatch(device):
        raise ValueError('one explicit physical GPU UUID is required')
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,name,memory.used,memory.total',
        '--format=csv,noheader,nounits', '-i', device], text=True)
    rows = list(csv.reader(raw.strip().splitlines(), skipinitialspace=True))
    if len(rows) != 1 or len(rows[0]) != 5 or rows[0][1] != device:
        raise ValueError('physical GPU identity differs')
    index, uuid, name, used, total = rows[0]
    processes = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
        '--format=csv,noheader,nounits'], text=True)
    occupied = [row for row in csv.reader(processes.strip().splitlines(), skipinitialspace=True)
                if row and row[0] == device]
    if occupied or int(used) > 256:
        raise ValueError('registered GPU is occupied; no process or power setting was changed')
    return dict(index=int(index), uuid=uuid, name=name, memory_used_mib=int(used),
                memory_total_mib=int(total), gpu_snapshot=raw, compute_snapshot=processes)
