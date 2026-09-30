"""Content identity of the tensors a Native worker actually uses for inference."""
from collections.abc import Mapping
import hashlib
import math
import re

from rwkv_lh.model_io import canonical_digest

TENSOR_IDENTITY_SCHEMA = 'rwkv-lh.runtime-weight-tensors.v1'
LOADED_IDENTITY_SCHEMA = 'rwkv-lh.loaded-weights.v1'
_SHA = re.compile(r'^[0-9a-f]{64}$')
_CHUNK_BYTES = 16 * 1024**2


def fingerprint_model(model):
    """Hash actual resident weights in logical tensor order, with bounded copies.

    Neither a model alias nor a file read after loading can prove which weights
    are resident. Include native runtime buffers and registered parameters so
    packed linear weights are covered too. Recurrent State belongs to the worker,
    outside this model weight collection.
    """
    import torch
    tensors = getattr(model, 'z', None)
    if not isinstance(tensors, Mapping) or not tensors:
        raise ValueError('Native loaded weight tensors are unavailable')
    values = {'runtime.' + name: value for name, value in tensors.items()}
    for method, prefix in (('named_parameters', 'parameter.'), ('named_buffers', 'buffer.')):
        values.update((prefix + name, value) for name, value in getattr(model, method, lambda: ())())
    records = []
    with torch.no_grad():
        for name, value in sorted(values.items()):
            if not isinstance(value, torch.Tensor) or value.layout != torch.strided:
                raise ValueError('Native loaded weight tensor layout is unsupported')
            if not value.numel():
                # vLLM's empty device/dtype marker is not an inference weight.
                continue
            tensor = value.detach()
            digest = hashlib.sha256()
            flat_rows = tensor.reshape(1) if tensor.ndim == 0 else tensor
            row_elements = math.prod(flat_rows.shape[1:])
            step = max(1, _CHUNK_BYTES // max(1, row_elements * tensor.element_size()))
            for begin in range(0, flat_rows.shape[0], step):
                chunk = flat_rows[begin:begin + step].to(device='cpu').contiguous()
                digest.update(chunk.view(torch.uint8).numpy().tobytes())
            records.append({'name': name, 'shape': list(tensor.shape), 'dtype': str(tensor.dtype),
                            'sha256': digest.hexdigest()})
    elements = sum(value.numel() for value in values.values())
    if not elements:
        raise ValueError('Native loaded weight tensors are empty')
    return {'schema_version': TENSOR_IDENTITY_SCHEMA, 'tensor_count': len(records),
            'tensor_elements': elements, 'tensors_sha256': canonical_digest(records)}


def validate_loaded_identity(value):
    message = 'Native serving loaded weight identity is missing or invalid'
    if not isinstance(value, Mapping) or set(value) != {'schema_version', 'workers'}:
        raise ValueError(message)
    workers = value['workers']
    if value['schema_version'] != LOADED_IDENTITY_SCHEMA or not isinstance(workers, list) or not workers:
        raise ValueError(message)
    for worker in workers:
        if (not isinstance(worker, Mapping)
                or set(worker) != {'schema_version', 'tensor_count', 'tensor_elements', 'tensors_sha256'}
                or worker['schema_version'] != TENSOR_IDENTITY_SCHEMA
                or any(type(worker[k]) is not int or worker[k] <= 0 for k in ('tensor_count', 'tensor_elements'))
                or not isinstance(worker['tensors_sha256'], str) or not _SHA.fullmatch(worker['tensors_sha256'])):
            raise ValueError(message)
    return value


def combine_workers(values):
    return validate_loaded_identity({'schema_version': LOADED_IDENTITY_SCHEMA, 'workers': [dict(v) for v in values]})


def identity_from_validation(result):
    stages = result.get('stages', [])
    loaded = [row for row in stages if isinstance(row, Mapping) and row.get('stage') == 'models_loaded']
    if len(loaded) != 1:
        raise ValueError('Native compatibility has no unique serving weight identity')
    return validate_loaded_identity(loaded[0].get('serving_weight_identity'))
