"""Hidden views through irwkv's own model, loader and FlashRWKV2 State pools.

This process-local adapter only arranges tensors. Model equations, numerical
kernels, weight preprocessing and the output projection stay in irwkv.
"""
from pathlib import Path
import tempfile
from types import SimpleNamespace


class DirectModel:
    def __init__(self, model, config):
        import torch
        self.model, self.config = model, config
        hf = model.config
        self.hidden_size = hf.hidden_size
        self.total_num_layers = hf.num_hidden_layers
        self.num_attention_heads = hf.num_attention_heads
        self.head_size = hf.head_size
        self.vocab_size = hf.vocab_size
        self.device = next(model.parameters()).device
        self.wkv_state_dtype = torch.float32
        self.layer = model.get_rwkv_state_layer()
        self.capacity = 0
        self.execution_profile = SimpleNamespace(wkv_mode='fp32io16',
            wkv_state_dtype='torch.float32', gemm_accumulation_policy='fp32')

    def zero_state(self, batch_size):
        import torch
        return [torch.zeros((self.total_num_layers, 2, batch_size, self.hidden_size),
                            device=self.device, dtype=torch.bfloat16),
                torch.zeros((self.total_num_layers, batch_size, self.num_attention_heads,
                             self.head_size, self.head_size), device=self.device, dtype=torch.float32),
                torch.zeros(batch_size, device=self.device, dtype=torch.long)]

    def forward_all_hidden(self, tokens, state):
        import torch
        from irwkv.forward_context import set_forward_context
        from irwkv.v1.attention.backends.rwkv_attn import RwkvAttentionMetadata
        if tokens.ndim != 2 or not tokens.numel():
            raise ValueError('direct irwkv requires a nonempty rectangular token batch')
        batch, length = tokens.shape
        expected = self.zero_state(batch)
        if len(state) != 3 or any(v.shape != e.shape or v.dtype != e.dtype or v.device != e.device
                                  for v, e in zip(state, expected)):
            raise ValueError('direct irwkv State geometry, dtype or device differs')
        if self.capacity < batch:
            self.layer.clear_kv_cache()
            page_bytes = self.layer.get_kv_cache_spec(self.config).page_size_bytes
            self.layer.bind_kv_cache(torch.zeros(page_bytes * batch, device=self.device, dtype=torch.int8))
            self.capacity = batch
        rows = torch.arange(batch, device=self.device, dtype=torch.int32)
        self.layer.materialize_state_slots(rows)
        self.layer._tmix_shift_pool[:, :batch].copy_(state[0][:, 0])
        self.layer._cmix_shift_pool[:, :batch].copy_(state[0][:, 1])
        self.layer._wkv_state_pool[:, :batch].copy_(state[1])
        metadata = RwkvAttentionMetadata(
            cu_seqlens=torch.arange(batch + 1, device=self.device, dtype=torch.int32) * length,
            state_indices=rows, batch_size=batch, max_seqlen=length,
            token_capacity=batch * length, sequence_capacity=batch, max_seqlen_capacity=length)
        metadata.validated_metadata = self.layer.prepare_metadata_ticket(metadata)
        with set_forward_context(metadata, self.config, num_tokens=tokens.numel()):
            hidden = self.model(tokens.reshape(-1), torch.zeros(tokens.numel(), device=self.device, dtype=torch.long))
        self.layer.materialize_state_slots(rows)
        state[0][:, 0].copy_(self.layer._tmix_shift_pool[:, :batch])
        state[0][:, 1].copy_(self.layer._cmix_shift_pool[:, :batch])
        state[1].copy_(self.layer._wkv_state_pool[:, :batch])
        state[2].add_(length)
        return hidden.reshape(batch, length, self.hidden_size)

    def project_logits_fp32(self, hidden):
        shape = hidden.shape[:-1]
        return self.model.compute_logits(hidden.reshape(-1, self.hidden_size)).reshape(*shape, self.vocab_size)

    def __call__(self, tokens, state, full_output=False):
        hidden = self.forward_all_hidden(tokens, state)
        return self.project_logits_fp32(hidden if full_output else hidden[:, -1])


def load_direct_model(path, *, runtime_temp):
    import os
    from rwkv_lh.gpu_resources import require_idle_gpu
    # Dedicated process required: never choose the first visible GPU implicitly.
    require_idle_gpu(os.environ.get('CUDA_VISIBLE_DEVICES'))
    import torch
    from irwkv.config import set_current_irwkv_config
    from irwkv.engine.arg_utils import EngineArgs
    from irwkv.distributed import init_distributed_environment, initialize_model_parallel
    from irwkv.model_executor.model_loader import get_model
    config = EngineArgs(model=str(path), dtype='bfloat16', enforce_eager=True,
        tensor_parallel_size=1, pipeline_parallel_size=1, mamba_ssm_cache_dtype='float32',
        mamba_cache_mode='none', enable_prefix_caching=False,
        enable_prompt_embeds=True, max_num_seqs=1).create_engine_config()
    Path(runtime_temp).mkdir(parents=True, exist_ok=True)
    if torch.distributed.is_initialized():
        raise RuntimeError('direct irwkv requires a dedicated fresh worker process')
    with tempfile.TemporaryDirectory(prefix='distributed-', dir=runtime_temp) as directory:
        with set_current_irwkv_config(config):
            init_distributed_environment(world_size=1, rank=0, local_rank=0,
                distributed_init_method='file://' + str(Path(directory) / 'rendezvous'), backend='nccl')
            initialize_model_parallel(tensor_model_parallel_size=1, pipeline_model_parallel_size=1)
            model = get_model(irwkv_config=config)
    return DirectModel(model, config)
