"""One atomic, resumable checkpoint containing trainable parameters only."""
import os
from pathlib import Path
import random
import tempfile
import torch
from . import statetune_core as core

SCHEMA='rwkv-lh.cc-view-optimizer-checkpoint.v1'


def save_last(path,model,optimizer,*,identity,progress):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    parameters={n:p.detach().cpu().clone() for n,p in model.named_parameters() if p.requires_grad}
    core.require(bool(parameters),'checkpoint has no trainable parameters')
    payload=dict(schema=SCHEMA,identity=dict(identity),progress=dict(progress),parameters=parameters,
        optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state(),python_rng=random.getstate(),
        cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [])
    pending=None
    try:
        with tempfile.NamedTemporaryFile(prefix=path.name+'-',suffix='.partial',dir=path.parent,delete=False) as stream:
            pending=Path(stream.name);torch.save(payload,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(pending,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if pending is not None:pending.unlink(missing_ok=True)
    return dict(path=str(path),sha256=core.sha256_file(path),progress=dict(progress))


def load_last(path,model,optimizer,*,identity):
    payload=torch.load(path,map_location='cpu',weights_only=True)
    core.require(payload['schema']==SCHEMA and payload['identity']==dict(identity),'checkpoint identity differs')
    parameters={n:p for n,p in model.named_parameters() if p.requires_grad}
    core.require(set(parameters)==set(payload['parameters']),'checkpoint trainable parameter set differs')
    for name,parameter in parameters.items():
        value=payload['parameters'][name]
        core.require(value.shape==parameter.shape and value.dtype==parameter.dtype and bool(torch.isfinite(value).all()),
                     'invalid checkpoint parameter: '+name)
    for state in payload['optimizer']['state'].values():
        core.require(all(not isinstance(v,torch.Tensor) or bool(torch.isfinite(v).all()) for v in state.values()),
                     'nonfinite optimizer state')
    with torch.no_grad():
        for name,parameter in parameters.items():parameter.copy_(payload['parameters'][name].to(parameter.device))
    optimizer.load_state_dict(payload['optimizer']);torch.set_rng_state(payload['torch_rng']);random.setstate(payload['python_rng'])
    if payload['cuda_rng']:
        core.require(torch.cuda.is_initialized() and len(payload['cuda_rng'])==torch.cuda.device_count(),'checkpoint CUDA RNG devices differ')
        torch.cuda.set_rng_state_all(payload['cuda_rng'])
    return payload['progress']
