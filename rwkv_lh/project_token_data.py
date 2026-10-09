"""Exact Native input replay and target-only candidate packing, without admission."""
import hashlib
from .project_contracts import digest
from .project_trace import role_boundaries
from .project_runtime import role_definitions
from .project_output_validation import validate_role_output
from .model_io import canonical_json, JSON_CALL_STOP_SUFFIXES
from .project_model_io import render_project_bootstrap
from .project_model_io import render_project_event_append, render_project_assignment
from .schema import ModelEvent
from .harness import ActionHarness
from .token_budget import tokenizer, VOCAB_PATH
from .project_input_delta import INPUT_HANDOFF_VERSION, input_update
from .project_decoder import build_role_decoder, available_definitions, tool_menu_update, INPUT_FRAMING, BOUNDARY_POLICY
from .project_protocols import executor
from .runtime.structured_output import decoder_receipt, state_output_token_ids


def _decode_generated_rwkv(tok, generated, finish_reason):
    """Decode text, retaining EOS in the original audited token sequence.

    Current RWKV tokenizer uses token 0 for BOS/EOS, outside its byte vocabulary.
    Only one terminal EOS on a natural stop is valid in a generated segment.
    """
    if not isinstance(generated, list) or any(type(t) is not int for t in generated):
        raise ValueError('original generation token IDs must be integers')
    text_ids = generated
    if 0 in generated:
        if finish_reason != 'stop' or generated[-1] != 0 or generated.count(0) != 1:
            raise ValueError('invalid RWKV EOS boundary')
        text_ids = generated[:-1]
    try:
        return tok.decode_bytes(text_ids).decode('utf-8')
    except (KeyError, UnicodeError) as exc:
        raise ValueError('invalid original generation vocabulary/text') from exc


def replay_native_rows(rows):
    """Rows must come from verified production role_boundaries, in ledger order."""
    lanes, result, checkpoints = {}, {}, {}
    tok = tokenizer()
    for row in rows:
        role, lane = row['role'], row['lane']
        if role == 'planner':
            continue
        {'executor': executor}[role].validate_input(row['input'])
        definitions = role_definitions(role, ActionHarness())
        exported = row['checkpoint']
        if exported['binding'].get('action_protocol') != executor.ACTION_PROTOCOL:
            raise ValueError('recorded action protocol differs from the role input')
        if exported['binding']['tools_digest'] != digest(definitions):
            raise ValueError('recorded tool definitions differ from current production')
        cp = exported['checkpoint']
        evidence = row['result']['evidence']
        raw = evidence.get('raw_generation', {})
        decoder_id = exported['binding'].get('decoder_catalog_sha256')
        if decoder_id is not None:
            decoder = build_role_decoder(definitions, role=role, payload=row['input'])
            if (decoder_id != build_role_decoder(definitions)['contract_sha256']
                    or exported['binding'].get('decoder_boundary_policy') != BOUNDARY_POLICY
                    or raw.get('decoder') != decoder_receipt(decoder)
                    or exported['binding'].get('decoder_input_framing') != INPUT_FRAMING):
                raise ValueError('recorded decoder contract/receipt differs from current role schema')
        elif (raw.get('decoder') is not None or raw.get('state_token_ids') is not None
              or any(key in exported['binding'] for key in
                     ('decoder_input_framing', 'decoder_boundary_policy', 'decoder_contract_sha256'))):
            raise ValueError('unbound decoder in original generation')
        if (raw.get('prompt_token_ids_scope') != 'full_context'
                or raw.get('input_bos_token_count') != 1 or raw.get('postprocessed') is not False):
            raise ValueError('original full-context Native tokens required')
        incremental = exported['binding'].get('input_handoff')
        if incremental != INPUT_HANDOFF_VERSION:
            raise ValueError('unknown recorded input handoff')
        retry, selected_parent = False, None
        if lane in lanes:
            previous, ids, prior_text = lanes[lane]
            if exported['binding']['action_protocol'] != previous['binding']['action_protocol']:
                raise ValueError('action protocol changed inside a recorded lane')
            if decoder_id != previous['binding'].get('decoder_catalog_sha256'):
                raise ValueError('decoder changed inside a recorded lane')
            if incremental != previous['binding'].get('input_handoff'):
                raise ValueError('input handoff changed inside a recorded lane')
            selected_parent, event, retry = input_update(role, lane, row['input'], previous)
            try:
                ids, prior_text = checkpoints[selected_parent['checkpoint_id']]
            except KeyError as exc:
                raise ValueError('retry anchor is absent from verified replay') from exc
            suffix = render_project_event_append(event, previous_transcript=selected_parent['transcript'],
                close_generation_anchor=decoder_id is not None,
                tool_update=tool_menu_update(definitions, role=role, payload=row['input'], checkpoint=previous, retry=retry)
                    if incremental else None)
            expected = [*ids, *tok.encode(suffix)]
            expected_text = prior_text + suffix
        else:
            suffix = render_project_bootstrap(available_definitions(definitions, role=role, payload=row['input']),
                                      render_project_assignment(row['input']))
            expected = [0, *tok.encode(suffix)]
            expected_text = suffix
        if raw.get('prompt_token_ids') != expected:
            raise ValueError('full server input token replay differs')
        original = raw['raw_output']
        generated = raw.get('raw_token_ids')
        state_tokens = generated
        if decoder_id is not None:
            state_tokens = state_output_token_ids(generated, raw.get('finish_reason'), decoder)
            if raw.get('state_token_ids') != state_tokens:
                raise ValueError('recorded decoder State output token IDs differ')
        decoded = _decode_generated_rwkv(tok, generated, raw.get('finish_reason'))
        allowed = [original]
        if raw.get('finish_reason') == 'stop' and decoder_id is None:
            allowed.extend(original + stop for stop in JSON_CALL_STOP_SUFFIXES)
        if decoded not in allowed:
            raise ValueError('original generation token/text mismatch')
        rejected = evidence.get('rejected') is True or evidence.get('known_budget_exhaustion') is True
        if cp['transcript'] != (suffix if rejected else original):
            raise ValueError('recorded committed/rolled-back State differs')
        if incremental:
            # Validate provenance independently of a caller's stored patch.
            input_update(role, lane, row['input'], exported)
            state = exported['input_state']
            if state['payload'] != row['input'] or state['rejected'] != rejected:
                raise ValueError('recorded input state differs from actual role boundary')
            if retry:
                old_state = lanes[lane][0]['input_state']
                if (state['anchor_input'] != old_state['anchor_input']
                        or state['anchor_checkpoint'] != old_state['anchor_checkpoint']):
                    raise ValueError('retry changed the clean anchor')
            else:
                anchor = state['anchor_checkpoint']
                if (state['anchor_input'] != row['input'] or anchor['transcript'] != suffix
                        or anchor['parent_checkpoint_id'] != (selected_parent['checkpoint_id'] if selected_parent else None)
                        or anchor['checkpoint_id'] != (cp['checkpoint_id'] if rejected else cp['parent_checkpoint_id'])):
                    raise ValueError('recorded input anchor differs from actual Native parent')
                checkpoints[anchor['checkpoint_id']] = (expected, expected_text)
        result[row['operation_id']] = {'row': row, 'input_token_ids': expected,
            'input_text': expected_text,
            'model_sha256': exported['binding']['model_sha256'],
            'state_profile_id': exported['binding']['profile'],
            'state_profile_sha256': exported['binding']['profile_sha256']}
        next_ids = expected if rejected else [*expected, *state_tokens]
        next_text = expected_text if rejected else expected_text + decoded
        checkpoints[cp['checkpoint_id']] = (next_ids, next_text)
        lanes[lane] = (exported, next_ids, next_text)
    return result


def replay_native_inputs(source):
    return replay_native_rows(list(role_boundaries(source)))


def pack_executor_candidate(replayed, command, *, context_tokens):
    return _pack_project_candidate(replayed, command, role='executor', context_tokens=context_tokens)


def _pack_project_candidate(replayed, command, *, role, context_tokens):
    row = replayed['row']
    if row['role'] != role:
        raise ValueError(f'{role} source required')
    target_command = canonical_json(command)
    from .project_model_io import parse_role_call
    parsed, _ = parse_role_call(target_command, role=role, payload=row['input'])
    validate_role_output(role, row['input'], parsed, role_definitions(role, ActionHarness()))
    target = target_command + JSON_CALL_STOP_SUFFIXES[0]
    target_ids = tokenizer().encode(target)
    if tokenizer().decode_bytes(target_ids).decode('utf-8') != target:
        raise ValueError('target tokenizer round trip differs')
    inputs = replayed['input_token_ids']
    fits = len(inputs) + len(target_ids) - 1 <= context_tokens
    return {**{k: v for k, v in replayed.items() if k != 'row'},
        'source_operation_id': row['operation_id'], 'source_event_digest': row['source_event_digest'],
        'input_protocol': row['input_protocol'], 'input_digest': digest(row['input']),
        'tokenizer_sha256': hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest(),
        'target_text': target, 'target_token_ids': target_ids,
        'token_ids': inputs + target_ids, 'loss_mask': [0] * len(inputs) + [1] * len(target_ids),
        'mask_alignment': 'unshifted token positions; trainer must apply next-token shift',
        'context_tokens': context_tokens, 'fits_context': fits, 'truncated': False,
        'training_eligible': False, 'split': 'unassigned',
        'admission_gaps': ['independent source coverage', 'fixed regression admission']
            + ([] if fits else ['source exceeds registered training context'])}
