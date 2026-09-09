"""Independent FP64 closed-form checks of the actual Native wrapper backward.

Native forward is replaced by a same-shape dummy. These CPU mechanisms isolate
the five custom backward functions and explicit FP16 cast boundaries; they do
not claim CUDA forward or full-model S0 gradient equivalence. No oracle calls
pure_producer, differentiate, or autograd. Fixed B=1, T=1/17, seed and thresholds
retain the previously preregistered numerical mechanism.
"""
import math
import sys
from types import ModuleType, SimpleNamespace

import pytest
import torch

from rwkv_lh import statetune_native_model as m

W, H, D, R = 1024, 16, 64, 8
VOCAB = 128
SEED = 2026090826
RELATIVE_RMSE_LIMIT = 0.01
SCALED_MAX_LIMIT = 0.005
CASES = ("Producer_layer0", "Producer_layer1", "NextProducer_layer1", "Post", "ResidualFFN", "Head")


@pytest.fixture
def native_backward_fixture(monkeypatch):
    previous_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(2)
        # devices=[] avoids initializing CUDA merely to preserve CPU RNG state.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(SEED)
            vmod = ModuleType("vllm.model_executor.models.rwkv7")
            vmod.use_ln1_tmix_fusion = lambda b, t: t == 1
            vmod.use_tmix_lnx_warp = lambda *args: False
            vmod.select_path = lambda b, t: None
            for name in ("vllm", "vllm.model_executor", "vllm.model_executor.models"):
                monkeypatch.setitem(sys.modules, name, ModuleType(name))
            monkeypatch.setitem(sys.modules, vmod.__name__, vmod)

            def dummy_prod(x, first, att, native, pre_mix=None):
                values = [torch.zeros_like(x) for _ in range(7)]
                return (*values, values[3] if att.index == 0 else first)

            monkeypatch.setattr(m, "native_producer", dummy_prod)
            fast = SimpleNamespace(tmix_lnx_rkvres_xg=lambda b, t, c, h, y, *args: torch.zeros_like(y))
            v3a = SimpleNamespace(
                add_layer_norm_tmix_mix6_f16=lambda x, r, *args: (torch.zeros_like(x), *[torch.zeros_like(x) for _ in range(6)]),
                add_layer_norm_cmix_mix_f16=lambda x, r, *args: (torch.zeros_like(x), torch.zeros_like(x)),
            )
            monkeypatch.setattr(torch.ops, "vllm_rwkv7_fast_ops_fp16", fast)
            monkeypatch.setattr(torch.ops, "rwkv7_v3a_ops", v3a)

            class Keys:
                def __getitem__(self, key):
                    return None

            native = SimpleNamespace(
                z=Keys(), add_ln=lambda x, r, *args: (torch.zeros_like(x), torch.zeros_like(x)),
                cmix=lambda x, *args: torch.zeros_like(x), cmix_from_mixed=lambda x, *args: torch.zeros_like(x),
                linear_att_c2c=lambda x, *args: torch.zeros_like(x), add=lambda x, r: torch.zeros_like(x),
                ln=lambda x, *args: torch.zeros_like(x),
                project_logits_fp32=lambda x: torch.zeros(*x.shape[:-1], VOCAB, dtype=torch.float32),
            )
            blocks = [m.Block(W, H, (R, R, R, R), i, 4 * W).half() for i in (0, 1)]
            head = SimpleNamespace(ln_out=torch.nn.LayerNorm(W).half(), head=torch.nn.Linear(W, VOCAB, bias=False).half())
            for module in (*blocks, head.ln_out, head.head):
                for name, parameter in module.named_parameters():
                    with torch.no_grad():
                        if ("ln" in name and name.endswith("weight")) or (module is head.ln_out and name == "weight"):
                            parameter.copy_(1 + 0.1 * torch.randn_like(parameter))
                        elif name.endswith("bias"):
                            parameter.copy_(0.05 * torch.randn_like(parameter))
                        elif name.endswith("time_state"):
                            parameter.zero_()
                        elif parameter.ndim == 2:
                            parameter.copy_(torch.randn_like(parameter) / math.sqrt(parameter.shape[0] if name[-1:] in ("1", "2") else parameter.shape[-1]))
                        else:
                            parameter.copy_(0.2 * torch.randn_like(parameter))
                    parameter.requires_grad_(False)
            yield SimpleNamespace(blocks=blocks, head=head, native=native)
    finally:
        torch.set_num_threads(previous_threads)


def d(x):
    return x.detach().double()

def q(x):
    return x.to(torch.float16).double()

def weight(x):
    return d(x)

def linear(x, w):
    return q(x @ weight(w).T)

def linback(g, w):
    return q(q(g) @ weight(w))

def previous(x):
    return torch.cat([torch.zeros_like(x[:, :1]), x[:, :-1]], dim=1)

def mixed(x, k):
    return q(x + (previous(x) - x) * weight(k))

def mixback(g, k):
    a = weight(k)
    v = g * (1 - a)
    v[:, :-1] += g[:, 1:] * a
    return v

def norm(x, module, heads=1):
    z = x.reshape(*x.shape[:-1], heads, x.shape[-1] // heads)
    centered = z - z.mean(-1, keepdim=True)
    inv = (centered.square().mean(-1, keepdim=True) + module.eps).rsqrt()
    unit = centered * inv
    out = unit.reshape_as(x) * weight(module.weight) + weight(module.bias)
    return (out, (unit, inv, weight(module.weight), x.shape))

def normback(g, cache):
    unit, inv, gamma, shape = cache
    v = (g * gamma).reshape_as(unit)
    return (inv * (v - v.mean(-1, keepdim=True) - unit * (v * unit).mean(-1, keepdim=True))).reshape(shape)

def producer_vjp(x, first, att, gs):
    kinds = ('r', 'w', 'k', 'v', 'a', 'g')
    xx = {n: mixed(x, getattr(att, 'x_' + n)) for n in kinds}
    r = linear(xx['r'], att.receptance.weight)
    k = linear(xx['k'], att.key.weight)
    vbase = linear(xx['v'], att.value.weight)
    w1 = q(xx['w'] @ weight(att.w1))
    a1 = q(xx['a'] @ weight(att.a1))
    g1 = q(xx['g'] @ weight(att.g1))
    fused = x.shape[0] * x.shape[1] <= 4 and x.shape[-1] >= 1024
    wt = torch.tanh(w1)
    gg = torch.sigmoid(g1)
    a12 = q(a1 @ weight(att.a2))
    ag = torch.sigmoid(a12 + weight(att.a0))
    u = (k * weight(att.k_k)).reshape(*k.shape[:-1], H, D)
    mag = u.square().sum(-1, keepdim=True).sqrt()
    den = mag.clamp_min(1e-12)
    unit = u / den
    kk = unit.reshape_as(k)
    gr, gw, gknew, gv, gaa, gb, ggout, gfirst = [d(g) for g in gs]
    gkk = -gaa + gb * ag
    gag = gknew * k * weight(att.k_a) + gb * kk
    gu = gkk.reshape_as(unit)
    gu = torch.where(mag > 1e-12, (gu - unit * (gu * unit).sum(-1, keepdim=True)) / den, gu / 1e-12)
    gk = gknew * (1 - weight(att.k_a) + weight(att.k_a) * ag) + gu.reshape_as(k) * weight(att.k_k)
    ga12 = q(gag * ag * (1 - ag))
    ga1 = q(ga12 @ weight(att.a2).T)
    gactw = gw @ weight(att.w2).T
    gactg = ggout @ weight(att.g2).T
    if not fused:
        gactw = q(gactw)
        gactg = q(gactg)
    gw1 = q(gactw * (1 - wt.square()))
    gg1 = q(gactg * gg * (1 - gg))
    gx = {n: torch.zeros_like(x) for n in kinds}
    gx['r'] = linback(gr, att.receptance.weight)
    gx['k'] = linback(gk, att.key.weight)
    gx['w'] = q(gw1 @ weight(att.w1).T)
    gx['a'] = q(ga1 @ weight(att.a1).T)
    gx['g'] = q(gg1 @ weight(att.g1).T)
    if att.index == 0:
        gvbase = gv + gfirst
        gf = torch.zeros_like(first)
    else:
        v1 = q(xx['v'] @ weight(att.v1))
        v12 = v1 @ weight(att.v2)
        if not fused:
            v12 = q(v12)
        vg = torch.sigmoid(v12 + weight(att.v0))
        gvbase = gv * (1 - vg)
        gf = gfirst + gv * vg
        gv12 = gv * (first - vbase) * vg * (1 - vg)
        if not fused:
            gv12 = q(gv12)
        gv1 = q(gv12 @ weight(att.v2).T)
        gx['v'] += q(gv1 @ weight(att.v1).T)
    gx['v'] += linback(gvbase, att.value.weight)
    return (q(sum((mixback(gx[n], getattr(att, 'x_' + n)) for n in kinds))), q(gf))

def post_vjp(y, r, k, v, g, att, up):
    normalized, ncache = norm(y, att.ln_x, H)
    rr = r.reshape(*r.shape[:-1], H, D)
    kk = k.reshape_as(rr)
    vv = v.reshape_as(rr)
    rk = weight(att.r_k)
    scalar = (rr * kk * rk).sum(-1, keepdim=True)
    dgated = linback(up, att.output.weight)
    dpre = dgated * g
    dy = normback(dpre, ncache)
    gg = dgated * (normalized + (scalar * vv).reshape_as(g))
    dd = dpre.reshape_as(rr)
    ds = (dd * vv).sum(-1, keepdim=True)
    return tuple((q(z) for z in [dy, (ds * kk * rk).reshape_as(r), (ds * rr * rk).reshape_as(k), (dd * scalar).reshape_as(v), gg]))

def ffn_vjp(x, attention, block, gr, gout):
    n, cache = norm(x + attention, block.ln2)
    n = q(n)
    a = mixed(n, block.ffn.x_k)
    up = linear(a, block.ffn.key.weight)
    dact = linback(gout, block.ffn.value.weight)
    dup = q(dact * 2 * up.clamp_min(0))
    dmixed = linback(dup, block.ffn.key.weight)
    dn = q(mixback(dmixed, block.ffn.x_k))
    ds = normback(dn, cache)
    return (q(gr + ds), q(gr + ds))

def head_vjp(x, ffn, model, up):
    n, cache = norm(q(x + ffn), model.ln_out)
    dn = q(up @ weight(model.head.weight))
    ds = q(normback(dn, cache))
    return (ds, ds)

def metric(actual, expected):
    ref = d(expected)
    act = torch.zeros_like(ref) if actual is None else d(actual)
    finite = bool(torch.isfinite(ref).all() and torch.isfinite(act).all())
    err = act - ref
    normref = float(ref.norm())
    rmse = float(err.square().mean().sqrt())
    rel = float(err.norm() / ref.norm()) if normref else 0.0
    scale = max(1.0, float(ref.abs().max()))
    scaled = float(err.abs().max()) / scale
    passed = finite and (actual is not None if normref else float(act.abs().max()) == 0.0) and (rel <= RELATIVE_RMSE_LIMIT) and (scaled <= SCALED_MAX_LIMIT)
    return {'passed': passed, 'relative_rmse': rel, 'rmse': rmse, 'max_abs': float(err.abs().max()), 'scaled_max_abs': scaled, 'reference_l2': normref, 'actual_none': actual is None, 'finite': finite}


def test_native_wrapper_vjps_match_independent_closed_form(native_backward_fixture):
    fixture = native_backward_fixture
    checks_seen = cases_seen = 0
    for tokens in (1, 17):
        for case in CASES:
            block = fixture.blocks[0 if case.endswith("layer0") else 1]
            att = block.att
            count = 5 if case == "Post" else 3 if case == "NextProducer_layer1" else 2
            inputs = tuple((0.2 * torch.randn(1, tokens, W, dtype=torch.float16)).requires_grad_() for _ in range(count))
            if case.startswith("Producer"):
                outputs = m.Producer.apply(*inputs, att, fixture.native)
            elif case.startswith("NextProducer"):
                outputs = m.NextProducer.apply(*inputs, block, fixture.native)
            elif case == "Post":
                outputs = m.Post.apply(*inputs, att, fixture.native)
            elif case == "ResidualFFN":
                outputs = m.ResidualFFN.apply(*inputs, block, fixture.native)
            else:
                outputs = m.Head.apply(*inputs, fixture.head, fixture.native)
            if isinstance(outputs, torch.Tensor):
                outputs = (outputs,)
            upstream = tuple(0.05 * torch.randn_like(value) for value in outputs)
            actual = torch.autograd.grad(outputs, inputs, upstream, allow_unused=True)
            with torch.no_grad():
                values = [d(value) for value in inputs]
                gradients = [d(value) for value in upstream]
                if case.startswith("Producer"):
                    expected = producer_vjp(*values, att, gradients)
                elif case.startswith("NextProducer"):
                    normalized, cache = norm(values[0] + values[1], block.ln1)
                    gx, gfirst = producer_vjp(q(normalized), values[2], att, gradients[1:])
                    summed_grad = normback(gx, cache)
                    expected = q(gradients[0] + summed_grad), q(gradients[0] + summed_grad), gfirst
                elif case == "Post":
                    expected = post_vjp(*values, att, gradients[0])
                elif case == "ResidualFFN":
                    expected = ffn_vjp(*values, block, *gradients)
                else:
                    expected = head_vjp(*values, fixture.head, gradients[0])
            assert len(actual) == len(expected)
            for index, (value, reference) in enumerate(zip(actual, expected)):
                check = metric(value, reference)
                assert check["passed"], (case, tokens, index, check)
                checks_seen += 1
            cases_seen += 1
    assert (cases_seen, checks_seen) == (12, 32)
