"""Fail startup if the actual sampler ignores the production transcript mask.

This first-token canary checks the live decoding path. Full schema controls and
model quality remain separate runtime experiments; this does not certify them.
"""
import asyncio
import hashlib
import json
from uuid import uuid4

from rwkv_lh.runtime.structured_output import build_transcript_decoder_contract, DECODER_BACKEND


def current_contract():
    from rwkv_lh.harness import ActionHarness
    from rwkv_lh.project_tools import configure_project_tools
    from rwkv_lh.project_protocols.executor import action_definitions
    harness = configure_project_tools(ActionHarness())
    return build_transcript_decoder_contract(action_definitions(harness.g1i_tool_definitions()))


def check_tokens(raw, constrained, forbidden, mask):
    if raw != [forbidden]:
        raise RuntimeError('decoder self-test negative control was not discriminating')
    if (len(constrained) != 1 or constrained[0] == forbidden
            or constrained[0] < 0 or constrained[0] // 8 >= len(mask)
            or not mask[constrained[0] // 8] & (1 << (constrained[0] % 8))):
        raise RuntimeError('decoder mask did not reject prohibited token or allow a legal token')


async def verify_runtime_decoder(engine, evidence):
    import llguidance
    from irwkv import TokensPrompt
    from irwkv.sampling_params import SamplingParams, StructuredOutputsParams, RequestOutputKind
    from irwkv.v1.structured_output.backend_guidance import GuidanceBackend
    config = engine.irwkv_config.structured_outputs_config
    if config.backend != DECODER_BACKEND:
        raise RuntimeError('native transcript requires the guidance backend')
    contract = current_contract()
    tokenizer = engine.renderer.get_tokenizer()
    wrapped = GuidanceBackend._build_ll_tokenizer(tokenizer, engine.model_config.get_vocab_size())
    matcher = llguidance.LLMatcher(wrapped, llguidance.LLMatcher.grammar_from_lark(contract['grammar']))
    mask = matcher.compute_bitmask()
    ids = tokenizer.encode('@', add_special_tokens=False)
    if len(ids) != 1 or mask[ids[0] // 8] & (1 << (ids[0] % 8)):
        raise RuntimeError('decoder self-test requires one prohibited vocabulary token')
    forbidden = ids[0]
    evidence.update(protocol='rwkv-lh.decoder-runtime-canary.v1', contract=contract,
        forbidden_token_id=forbidden, initial_mask_sha256=hashlib.sha256(mask).hexdigest(),
        scope='live first-token mask; full schema acceptance is a separate verification', requests=[])
    outputs = []
    for constrained in (False, True):
        request_id = 'decoder-startup-' + uuid4().hex
        structured = StructuredOutputsParams(grammar=contract['grammar']) if constrained else None
        if structured is not None: structured._backend = DECODER_BACKEND
        settings = dict(max_tokens=1,temperature=0.0,top_p=1.0,top_k=-1,min_p=0.0,
            repetition_penalty=1.0,presence_penalty=0.0,frequency_penalty=0.0,penalty_decay=1.0,
            seed=20261029,logit_bias={forbidden:100.0},output_kind=RequestOutputKind.FINAL_ONLY,
            structured_outputs=structured)
        row = dict(request_id=request_id,prompt_token_ids=[0],constrained=constrained,
            sampling={k:v for k,v in settings.items() if k not in ('structured_outputs','output_kind')})
        evidence['requests'].append(row)

        async def collect():
            final = None
            async for result in engine.generate(TokensPrompt(prompt_token_ids=[0]),SamplingParams(**settings),request_id):
                final=result
            if final is None or len(final.outputs)!=1:
                raise RuntimeError('decoder self-test returned no unique completion')
            result=final.outputs[0]
            row.update(token_ids=list(result.token_ids),text=result.text,finish_reason=result.finish_reason)
            return list(result.token_ids)

        try:
            outputs.append(await asyncio.wait_for(collect(), timeout=120))
        except BaseException:
            await engine.abort(request_id)
            raise
    check_tokens(*outputs, forbidden, mask)
    evidence['passed'] = True
    return dict(protocol=evidence['protocol'],passed=True,grammar_sha256=contract['grammar_sha256'],
                evidence_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest())
