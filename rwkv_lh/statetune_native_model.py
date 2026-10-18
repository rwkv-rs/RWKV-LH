"""Native RWKV7 StateTune: exact serving forward and derivatives of the same equations."""
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint
from rwkv_lh.rwkv7_layout import RWKV7Layout

def mix(x, weight, previous_token):
    """Token shift; previous_token [B,C] is the carried last input of the preceding chunk."""
    previous = torch.cat((previous_token.unsqueeze(1).to(x.dtype), x[:, :-1]), dim=1)
    return torch.addcmul(x.float(), previous.float() - x.float(), weight.float()).half()

class Attention(nn.Module):

    def __init__(self, width, heads, ranks, index):
        super().__init__()
        self.index, self.heads = (index, heads)
        for name in ('x_r', 'x_w', 'x_k', 'x_v', 'x_a', 'x_g', 'w0', 'a0', 'v0', 'k_k', 'k_a'):
            self.register_parameter(name, nn.Parameter(torch.empty(1, 1, width)))
        for prefix, rank in zip(('w', 'a', 'v', 'g'), ranks):
            self.register_parameter(prefix + '1', nn.Parameter(torch.empty(width, rank)))
            self.register_parameter(prefix + '2', nn.Parameter(torch.empty(rank, width)))
        self.r_k = nn.Parameter(torch.empty(heads, width // heads))
        self.time_state = nn.Parameter(torch.empty(heads, width // heads, width // heads))
        for name in ('receptance', 'key', 'value', 'output'):
            setattr(self, name, nn.Linear(width, width, bias=False))
        self.ln_x = nn.GroupNorm(heads, width, eps=0.00064)

class ChannelMix(nn.Module):

    def __init__(self, width, intermediate):
        super().__init__()
        self.x_k = nn.Parameter(torch.empty(1, 1, width))
        self.key = nn.Linear(width, intermediate, bias=False)
        self.value = nn.Linear(intermediate, width, bias=False)

    def forward(self, x, previous_token):
        up = self.key(mix(x, self.x_k, previous_token))
        return self.value(F.relu(up.float()).square().half())

class Block(nn.Module):

    def __init__(self, width, heads, ranks, index, intermediate):
        super().__init__()
        if index == 0:
            self.ln0 = nn.LayerNorm(width)
        self.ln1, self.ln2 = (nn.LayerNorm(width), nn.LayerNorm(width))
        self.att = Attention(width, heads, ranks, index)
        self.ffn = ChannelMix(width, intermediate)

class NativeStateModel(nn.Module):

    def __init__(self, layout: RWKV7Layout):
        super().__init__()
        if layout.head_size != 64:
            raise ValueError('compiled Native recurrence requires head_size=64')
        width = layout.width
        ranks = (layout.decay_rank, layout.a_rank, layout.v_rank, layout.gate_rank)
        self.emb = nn.Embedding(layout.vocab, width)
        self.blocks = nn.ModuleList((Block(width, layout.heads, ranks, i, layout.intermediate) for i in range(layout.layers)))
        self.ln_out = nn.LayerNorm(width)
        self.head = nn.Linear(width, layout.vocab, bias=False)
        self.layout = layout

def norm_float(x, module):
    return F.layer_norm(x.float(), (x.shape[-1],), module.weight.float(), module.bias.float(), module.eps)

def pure_producer(x, first, shift, att):
    batch, tokens, width = x.shape
    shape = (batch, tokens, att.heads, width // att.heads)
    xr, xw, xk, xv, xa, xg = (mix(x, getattr(att, 'x_' + n), shift) for n in ('r', 'w', 'k', 'v', 'a', 'g'))
    r, k, v = (att.receptance(xr), att.key(xk), att.value(xv))
    w1, a1, g1 = (xw @ att.w1, xa @ att.a1, xg @ att.g1)
    fused = width >= 1024 and batch * tokens <= 4
    w = (torch.tanh(w1.float()) @ att.w2.float()).half() if fused else torch.tanh(w1.float()).half() @ att.w2
    a12 = a1 @ att.a2
    g = (torch.sigmoid(g1.float()) @ att.g2.float()).half() if fused else torch.sigmoid(g1.float()).half() @ att.g2
    if att.index == 0:
        first = v
    else:
        v1 = xv @ att.v1
        v12 = v1.float() @ att.v2.float() if fused else v1 @ att.v2
        gate = torch.sigmoid(v12.float() + att.v0.float())
        v = torch.addcmul(v.float(), first.float() - v.float(), gate).half()
    gate = torch.sigmoid(a12.float() + att.a0.float())
    kk = F.normalize((k.float() * att.k_k.float()).reshape(shape), dim=-1, eps=1e-12).reshape_as(k)
    new_k = (k.float() * (1 + (gate - 1) * att.k_a.float())).half()
    return (r, w, new_k, v, (-kk).half(), (kk * gate).half(), g, first)

def native_producer(x, first, shift, att, native, pre_mix=None):
    from vllm.model_executor.models.rwkv7 import select_path, use_tmix_mix6_3d
    batch, tokens, width = x.shape
    p = f'blocks.{att.index}.att.'
    z = native.z
    if pre_mix is None:
        ops = torch.ops.vllm_rwkv7_fast_ops_fp16
        op = ops.tmix_mix6_3d if use_tmix_mix6_3d(batch, tokens, width) else ops.tmix_mix6
        # The kernel reads the carried token and overwrites its buffer in place.
        pre_mix = op(batch, tokens, width, x.contiguous(), shift.clone().contiguous(), *(z[p + 'x_' + n] for n in ('r', 'w', 'k', 'v', 'a', 'g')))
    return native._project_tmix(att.index, *pre_mix, first, p, select_path(batch, tokens), batch_size=batch, time_steps=tokens)

def differentiate(ctx, fn, upstream):
    """Recompute the same equation and its actual derivative; never a detached bypass."""
    saved = ctx.saved_tensors
    with torch.enable_grad():
        inputs = [value.detach().requires_grad_(ctx.needs_input_grad[i]) for i, value in enumerate(saved)]
        outputs = fn(*inputs)
        if isinstance(outputs, torch.Tensor):
            outputs = (outputs,)
        pairs = [(out, grad) for out, grad in zip(outputs, upstream) if out.requires_grad and grad is not None]
        active = [value for value in inputs if value.requires_grad]
        grads = torch.autograd.grad([x for x, _ in pairs], active, [g.to(x) for x, g in pairs], allow_unused=True) if pairs else [None] * len(active)
    iterator = iter(grads)
    return tuple((next(iterator) if value.requires_grad else None for value in inputs))

class Producer(torch.autograd.Function):

    @staticmethod
    def forward(ctx, x, first, shift, att, native):
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(x, first, shift)
        ctx.att = att
        return native_producer(x, first, shift, att, native)

    @staticmethod
    def backward(ctx, *grads):
        return (*differentiate(ctx, lambda x, f, s: pure_producer(x, f, s, ctx.att), grads), None, None)

class NextProducer(torch.autograd.Function):

    @staticmethod
    def forward(ctx, x, ffn, first, shift, block, native):
        """Returns (residual, carried att shift, producer outputs)."""
        from vllm.model_executor.models.rwkv7 import use_ln1_tmix_fusion
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(x, ffn, first, shift)
        ctx.block = block
        batch, tokens, width = x.shape
        p = f'blocks.{block.att.index}.'
        z = native.z
        if use_ln1_tmix_fusion(batch, tokens):
            # The fused kernel writes the normalized last token into its shift buffer.
            carried = shift.clone().contiguous()
            values = torch.ops.rwkv7_v3a_ops.add_layer_norm_tmix_mix6_f16(x.contiguous(), ffn.contiguous(), carried, z[p + 'ln1.weight'], z[p + 'ln1.bias'], *(z[p + 'att.x_' + n] for n in ('r', 'w', 'k', 'v', 'a', 'g')))
            residual, pre_mix = (values[0], values[1:])
            produced = native_producer(residual, first, shift, block.att, native, pre_mix)
        else:
            residual, normalized = native.add_ln(x, ffn, z[p + 'ln1.weight'], z[p + 'ln1.bias'])
            carried = normalized[:, -1].clone()
            produced = native_producer(normalized, first, shift, block.att, native)
        return (residual, carried, *produced)

    @staticmethod
    def backward(ctx, *grads):

        def equation(x, ffn, first, shift):
            summed = x.float() + ffn.float()
            normalized = norm_float(summed, ctx.block.ln1).half()
            return (summed.half(), normalized[:, -1], *pure_producer(normalized, first, shift, ctx.block.att))
        return (*differentiate(ctx, equation, grads), None, None)

class Post(torch.autograd.Function):

    @staticmethod
    def forward(ctx, y, r, k, v, g, att, native):
        from vllm.model_executor.models.rwkv7 import use_tmix_lnx_warp
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(y, r, k, v, g)
        ctx.att = att
        batch, tokens, width = r.shape
        heads = att.heads
        p = f'blocks.{att.index}.att.'
        z = native.z
        ops = torch.ops.vllm_rwkv7_fast_ops_fp16
        op = ops.tmix_lnx_rkvres_xg_warp if use_tmix_lnx_warp(batch, tokens, width, heads) else ops.tmix_lnx_rkvres_xg
        value = op(batch, tokens, width, heads, y.contiguous(), r.contiguous(), k.contiguous(), v.contiguous(), z[p + 'r_k'], z[p + 'ln_x.weight'], z[p + 'ln_x.bias'], g.contiguous())
        return native.linear_att_c2c(value, z[p + 'output.weight'], batch * tokens)

    @staticmethod
    def backward(ctx, *grads):

        def equation(y, r, k, v, g):
            att = ctx.att
            batch, tokens, width = r.shape
            shape = (batch, tokens, att.heads, width // att.heads)
            normalized = F.group_norm(y.float().reshape(batch * tokens, width), att.heads, att.ln_x.weight.float(), att.ln_x.bias.float(), att.ln_x.eps).reshape(shape)
            residual = (r.float().reshape(shape) * k.float().reshape(shape) * att.r_k.float()).sum(-1, keepdim=True) * v.float().reshape(shape)
            return att.output(((normalized + residual).reshape_as(g) * g.float()).half())
        return (*differentiate(ctx, equation, grads), None, None)

class ResidualFFN(torch.autograd.Function):

    @staticmethod
    def forward(ctx, x, attention, shift, block, native):
        """Returns (residual, channel-mix output, carried ffn shift)."""
        from vllm.model_executor.models.rwkv7 import select_path
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(x, attention, shift)
        ctx.block = block
        batch, tokens, width = x.shape
        p = f'blocks.{block.att.index}.'
        z = native.z
        if tokens == 1:
            # The fused kernel writes the normalized token into its shift buffer.
            carried = shift.clone().contiguous()
            residual, mixed = torch.ops.rwkv7_v3a_ops.add_layer_norm_cmix_mix_f16(x.contiguous(), attention.contiguous(), carried, z[p + 'ln2.weight'], z[p + 'ln2.bias'], z[p + 'ffn.x_k'])
            out = native.cmix_from_mixed(mixed, p + 'ffn.', select_path(batch, tokens))
        else:
            residual, normalized = native.add_ln(x, attention, z[p + 'ln2.weight'], z[p + 'ln2.bias'])
            # Serving layout [att, ffn]; cmix reads and overwrites only index 1.
            pair = torch.stack((torch.zeros_like(shift), shift)).contiguous()
            out = native.cmix(normalized, pair, p + 'ffn.', select_path(batch, tokens))
            carried = normalized[:, -1].clone()
        return (residual, out, carried)

    @staticmethod
    def backward(ctx, *grads):

        def equation(x, attention, shift):
            summed = x.float() + attention.float()
            normalized = norm_float(summed, ctx.block.ln2).half()
            return (summed.half(), ctx.block.ffn(normalized, shift), normalized[:, -1])
        return (*differentiate(ctx, equation, grads), None, None)

class Head(torch.autograd.Function):

    @staticmethod
    def forward(ctx, x, ffn, model, native):
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(x, ffn)
        ctx.model = model
        hidden = native.ln(native.add(x, ffn), native.z['ln_out.weight'], native.z['ln_out.bias'])
        return native.project_logits_fp32(hidden)

    @staticmethod
    def backward(ctx, *grads):
        if grads[0] is None:
            return (None, None, None, None)
        # The frozen linear projection needs only dlogits @ weight. Rebuilding
        # its forward activation costs another full [B,T,vocab] FP32 tensor
        # (6 GiB at T=24576), although it contributes nothing to this derivative.
        hidden_grad = grads[0].float() @ ctx.model.head.weight.float()
        def equation(x, ffn):
            return norm_float((x.float() + ffn.float()).half(), ctx.model.ln_out).half()
        return (*differentiate(ctx, equation, (hidden_grad,)), None, None)

class NativeGradientModel(NativeStateModel):

    def layer(self, x, previous_ffn, first, wkv, att_shift, ffn_shift, index):
        """One block. wkv=None starts from this layer's trainable time_state.

        Returns the block outputs and the layer's final serving State: FP32 wkv
        [1,H,K,V] and the FP16 normalized last tokens consumed by the next chunk's
        att and ffn token shift (serving shift_state[0] and [1]).
        """
        from rwkv_lh.statetune_native_recurrence import recurrent
        block = self.blocks[index]
        native = self.native
        if index == 0:
            normalized = native.ln(x, native.z['blocks.0.ln1.weight'], native.z['blocks.0.ln1.bias'])
            att_carried = normalized[:, -1].clone()
            values = Producer.apply(normalized, first, att_shift, block.att, native)
        else:
            values = NextProducer.apply(x, previous_ffn, first, att_shift, block, native)
            x, att_carried, values = (values[0], values[1], values[2:])
        r, w, k, v, aa, b, g, first = values
        batch, tokens, width = r.shape
        shape = (batch, tokens, block.att.heads, width // block.att.heads)
        if wkv is None:
            wkv = block.att.time_state.transpose(-1, -2).unsqueeze(0).expand(batch, -1, -1, -1)
        y, wkv_carried = recurrent(*(value.reshape(shape).contiguous() for value in (r, w, k, v, aa, b)), initial_state=wkv.contiguous(), decay_bias=block.att.w0.reshape(shape[-2:]).contiguous())
        attention = Post.apply(y.reshape_as(r), r, k, v, g, block.att, native)
        x, ffn, ffn_carried = ResidualFFN.apply(x, attention, ffn_shift, block, native)
        return (x, ffn, first, wkv_carried, att_carried, ffn_carried)

    def forward(self, tokens, state=None, *, return_state=False):
        """Logits for one chunk. state=None is the episode start (time_state, zero shifts);
        otherwise it is the previous chunk's returned per-layer (wkv, att_shift, ffn_shift)."""
        if (tokens.ndim != 2 or tokens.shape[0] != 1 or tokens.shape[1] < 1
                or tokens.shape[1] > getattr(self, 'context_tokens', tokens.shape[1])):
            raise ValueError('Native StateTune supports one complete chunk of one sample per forward')
        x = self.native.embed(tokens)
        width, heads = x.shape[-1], self.blocks[0].att.heads
        if state is None:
            zero = x.new_zeros(1, width)
            state = [(None, zero, zero)] * len(self.blocks)
        elif not (len(state) == len(self.blocks) and all(
                len(layer) == 3 and layer[0].dtype == torch.float32
                and tuple(layer[0].shape) == (1, heads, width // heads, width // heads)
                and all(value.dtype == x.dtype and tuple(value.shape) == (1, width) for value in layer[1:])
                for layer in state)):
            raise ValueError('carried State must be one FP32 wkv and two token shifts per layer')
        first = x
        ffn = torch.zeros_like(x)
        carried = []
        for i in range(len(self.blocks)):
            function = lambda x, ffn, first, *layer_state, i=i: self.layer(x, ffn, first, *layer_state, i)
            x, ffn, first, *final = checkpoint(function, x, ffn, first, *state[i], use_reentrant=False) if torch.is_grad_enabled() else function(x, ffn, first, *state[i])
            carried.append(tuple(final))
        logits = Head.apply(x, ffn, self, self.native)
        return (logits, tuple(carried)) if return_state else logits

def build(spec):
    from rwkv_lh import statetune_core as a
    from vllm.config.compilation import CompilationConfig, CompilationMode
    from vllm.config.vllm import set_current_vllm_config
    from vllm.model_executor.models import rwkv7
    from vllm.transformers_utils.configs.rwkv7 import RWKV7Config
    import vllm.rwkv7_ops
    rwkv7.get_tensor_model_parallel_world_size = lambda: 1
    rwkv7.get_tensor_model_parallel_rank = lambda: 0
    config_values = json.loads((Path(spec['model_artifact']) / 'config.json').read_text())
    layout = RWKV7Layout.from_config(config_values)
    context_tokens = spec['context_tokens']
    a.require(type(context_tokens) is int and 0 < context_tokens <= config_values['context_length'],
              'Native training context exceeds the model artifact')
    a.require(layout.dtype == 'bfloat16', 'Native weight preprocessing currently validates BF16 checkpoints')
    config = RWKV7Config(**config_values)
    vc = SimpleNamespace(compilation_config=CompilationConfig(mode=CompilationMode.NONE), model_config=SimpleNamespace(hf_config=config, enforce_eager=True, dtype=torch.bfloat16, head_dtype=None), quant_config=None, parallel_config=None)
    with set_current_vllm_config(vc):
        native = rwkv7.RWKV7ForCausalLM(vllm_config=vc)
    with torch.device('meta'):
        model = NativeGradientModel(layout)
    a.load_frozen_base(model, spec['base']['path'], spec['base']['sha256'], layers=layout.layers)
    initial = a.state_parameters(model, layers=layout.layers)
    raw = {name: value.detach() for name, value in model.named_parameters() if name not in initial}
    native._preprocess_weights(raw)
    native.z = raw
    for name, parameter in list(model.named_parameters()):
        module, key = name.rsplit('.', 1)
        if name in initial:
            value = torch.zeros(parameter.shape, device='cuda:0', dtype=torch.float32)
        elif name == 'emb.weight':
            value = parameter.detach().to(device='cuda:0', dtype=torch.float16)
        else:
            value = native.z[name]
            if not rwkv7.is_lowrank_weight(name) and any((part in name for part in ('key.weight', 'value.weight', 'receptance.weight', 'output.weight', 'head.weight'))):
                value = value.t()
            value = value.reshape(parameter.shape)
        model.get_submodule(module)._parameters[key] = nn.Parameter(value, requires_grad=name in initial)
    object.__setattr__(model, 'native', native)
    model.context_tokens = context_tokens
    a.freeze_for_state_tuning(model, layers=layout.layers)
    model.eval()
    return model
