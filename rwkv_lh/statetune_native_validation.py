"""Shared numerical coverage rules for the validator and training admission."""
from collections.abc import Mapping
import math

from .statetune_core import require


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_plan(plan):
    message = 'Native compatibility registration must cover the complete target context'
    context = plan.get('context_tokens')
    require(type(context) is int and context > 0, message)
    for field in ('alignment_lengths', 'backward_lengths'):
        lengths = plan.get(field)
        require(isinstance(lengths, list) and bool(lengths)
                and all(type(n) is int and 0 < n <= context for n in lengths)
                and context in lengths, message)
    require(type(plan.get('state_seed')) is int and 0 <= plan['state_seed'] < 2**63
            and _finite(plan.get('state_scale')) and plan['state_scale'] > 0,
            'Native compatibility requires a registered nonzero State generation plan')
    require(plan.get('purpose') == 'numerical_mechanism_only'
            and type(plan.get('optimizer_steps')) is int and plan['optimizer_steps'] == 0
            and _finite(plan.get('max_logit_error')) and plan['max_logit_error'] == 0
            and _finite(plan.get('max_seconds')) and plan['max_seconds'] > 0
            and type(plan.get('max_allocated_bytes')) is int and plan['max_allocated_bytes'] > 0,
            'Native compatibility numerical limits are invalid')


def validate_result(plan, result):
    """Require every registered repetition and both States, plus full backward.

    Stage order is the actual validator order. A short run, duplicate record,
    success flag or completion marker cannot stand in for missing evidence.
    """
    validate_plan(plan)
    message = 'Native compatibility evidence has incomplete or failed numerical coverage'
    elapsed = result.get('elapsed_seconds')
    require(result.get('passed') is True and 'error' not in result
            and type(result.get('optimizer_steps')) is int and result['optimizer_steps'] == 0
            and type(result.get('role_samples')) is int and result['role_samples'] == 0
            and _finite(elapsed) and 0 <= elapsed <= plan['max_seconds'], message)
    stages = result.get('stages')
    expected = (['identity_admitted', 'models_loaded']
                + ['all_vocab_alignment'] * (2 * len(plan['alignment_lengths']))
                + ['full_model_backward'] * len(plan['backward_lengths']) + ['complete'])
    require(isinstance(stages, list) and all(isinstance(s, Mapping) for s in stages)
            and [s.get('stage') for s in stages] == expected, message)
    require(stages[0].get('gpu_uuid') == plan.get('gpu_uuid') and bool(plan.get('gpu_uuid')), message)
    loaded = stages[1]
    layout = loaded.get('layout')
    require(isinstance(layout, Mapping)
            and all(type(layout.get(k)) is int and layout[k] > 0
                    for k in ('layers', 'heads', 'head_size', 'vocab')), message)
    require(loaded.get('state_shape') == [layout['layers'], layout['heads'], layout['head_size'], layout['head_size']]
            and loaded.get('tokenizer_vocab_size') == layout['vocab']
            and type(loaded.get('bos_token_id')) is int and 0 <= loaded['bos_token_id'] < layout['vocab'], message)
    position = 2
    for state in ('zero', 'nonzero'):
        for length in plan['alignment_lengths']:
            stage = stages[position]
            position += 1
            error = stage.get('max_absolute_error')
            require(stage.get('state') == state and type(stage.get('tokens')) is int and stage['tokens'] == length
                    and type(stage.get('compared_logits')) is int and stage['compared_logits'] == length * layout['vocab']
                    and stage.get('comparison_passed') is True and _finite(error)
                    and 0 <= error <= plan['max_logit_error'], message)
    names = {f'blocks.{i}.att.time_state' for i in range(layout['layers'])}
    for length in plan['backward_lengths']:
        stage = stages[position]
        position += 1
        gradients = stage.get('gradients')
        require(type(stage.get('tokens')) is int and stage['tokens'] == length
                and isinstance(gradients, Mapping) and set(gradients) == names
                and all(isinstance(v, Mapping) and v.get('finite') is True and v.get('nonzero') is True
                        for v in gradients.values())
                and all(stage.get(k) is True for k in ('prompt_loss_gradient_zero', 'base_unchanged', 'state_unchanged'))
                and _finite(stage.get('loss')) and stage['loss'] >= 0
                and type(stage.get('peak_allocated_bytes')) is int
                and 0 <= stage['peak_allocated_bytes'] <= plan['max_allocated_bytes'], message)
    require(stages[-1].get('independent_samples_equal') is True
            and stages[-1].get('binary_inventory_verified') is True, message)


def validate_carry_plan(plan):
    """Registered coverage of chunked State-carry training against serving persistent State.

    Alignment plans compare every chunk's all-vocabulary logits and carried
    State with serving that keeps one recurrent State across the same chunks.
    Gradient plans compare chunked backward with one full-sequence backward;
    long plans exceed the context and measure memory and recompute identity.
    Each plan must contain a chunk without targets and a full-context chunk
    must be covered, so carry through an unsupervised chunk is exercised.
    """
    message = 'State-carry registration is incomplete or invalid'
    context = plan.get('context_tokens')
    require(type(context) is int and context > 0, message)

    def chunks_valid(row, *, longest):
        starts = row.get('chunk_starts') if isinstance(row, Mapping) else None
        total = row.get('tokens') if isinstance(row, Mapping) else None
        if not (type(total) is int and isinstance(starts, list) and len(starts) >= 3 and starts[0] == 0
                and all(type(a) is int and a < b for a, b in zip(starts, [*starts[1:], total]))):
            return False
        sizes = [b - a for a, b in zip(starts, [*starts[1:], total])]
        return max(sizes) <= context and total <= longest

    for field, longest in (('alignment_plans', None), ('gradient_plans', context), ('long_backward_plans', None)):
        rows = plan.get(field)
        require(isinstance(rows, list) and bool(rows)
                and all(chunks_valid(row, longest=longest or 2**31) for row in rows), message)
    for field in ('alignment_plans', 'gradient_plans', 'long_backward_plans'):
        require(any(context in [b - a for a, b in zip(r['chunk_starts'], [*r['chunk_starts'][1:], r['tokens']])]
                    or field == 'gradient_plans' for r in plan[field]), message)
    require(any(1 in [b - a for a, b in zip(r['chunk_starts'], [*r['chunk_starts'][1:], r['tokens']])]
                for r in plan['alignment_plans']), 'State-carry alignment must cover a single-token chunk')
    require(any(r['tokens'] == context for r in plan['gradient_plans'])
            and all(r['tokens'] > context for r in plan['long_backward_plans']), message)
    require(type(plan.get('state_seed')) is int and 0 <= plan['state_seed'] < 2**63
            and _finite(plan.get('state_scale')) and plan['state_scale'] > 0
            and plan.get('purpose') == 'numerical_mechanism_only'
            and type(plan.get('optimizer_steps')) is int and plan['optimizer_steps'] == 0
            and _finite(plan.get('max_logit_error')) and plan['max_logit_error'] == 0
            and _finite(plan.get('max_gradient_relative_error')) and 0 < plan['max_gradient_relative_error'] < 1
            and _finite(plan.get('max_loss_relative_error')) and 0 < plan['max_loss_relative_error'] < 1
            and _finite(plan.get('max_seconds')) and plan['max_seconds'] > 0
            and type(plan.get('max_allocated_bytes')) is int and plan['max_allocated_bytes'] > 0
            and isinstance(plan.get('gpu_uuid'), str) and plan['gpu_uuid'].startswith('GPU-'), message)
