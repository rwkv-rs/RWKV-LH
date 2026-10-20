"""Explicit B-only vLLM plugins; never registered by the product entry point."""
from copy import copy

from .cc_view_decoder import EXTENSION, extract_grammar, forced_think_suffix, token_continues_suffix, think_limited_prefix
from .cc_view_experiment import PROTOCOL, THINK_LIMIT


class CCGrammarEngine:
    """Translate this view's attested decoder into a guidance grammar request."""
    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def generate(self, prompt, params, request_id, *args, **kwargs):
        from vllm.sampling_params import StructuredOutputsParams
        from .runtime.structured_output import build_decoder_contract, DECODER_BACKEND
        structured = params.structured_outputs
        if structured is not None and isinstance(structured.json, dict) and EXTENSION in structured.json:
            grammar = extract_grammar(build_decoder_contract(structured.json))
            params = copy(params)
            params.structured_outputs = StructuredOutputsParams(grammar=grammar)
            params.structured_outputs._backend = DECODER_BACKEND
        return self.engine.generate(prompt, params, request_id, *args, **kwargs)


def install_decoder_backend():
    """Registered only in the frozen B deployment's general-plugin overlay."""
    import torch
    from vllm.v1.structured_output import backend_guidance as native
    OriginalBackend, OriginalGrammar = native.GuidanceBackend, native.GuidanceGrammar
    if getattr(OriginalBackend, 'cc_view_protocol', None) == PROTOCOL:
        return

    class CCGrammar(OriginalGrammar):
        def __init__(self, original, vocab):
            self.__dict__.update(original.__dict__)
            self.cc_vocab = vocab
            self.cc_tokens = []
            self.cc_masks = {}

        def accept_tokens(self, request_id, tokens):
            allowed=think_limited_prefix([self.cc_vocab[token] for token in self.cc_tokens],
                                         [self.cc_vocab[token] for token in tokens])
            if allowed!=len(tokens):
                return False
            accepted = super().accept_tokens(request_id, tokens)
            if accepted:
                self.cc_tokens.extend(tokens)
            return accepted

        def validate_tokens(self, tokens):
            valid=super().validate_tokens(tokens)
            count=think_limited_prefix([self.cc_vocab[token] for token in self.cc_tokens],
                                       [self.cc_vocab[token] for token in valid])
            return valid[:count]

        def rollback(self, count):
            super().rollback(count)
            if count:
                del self.cc_tokens[-count:]

        def reset(self):
            super().reset()
            self.cc_tokens.clear()

        def fill_bitmask(self, bitmask, idx):
            super().fill_bitmask(bitmask, idx)
            suffix = forced_think_suffix([self.cc_vocab[token] for token in self.cc_tokens])
            if suffix is None:
                return
            if suffix not in self.cc_masks:
                words = [0] * ((self.vocab_size + 31) // 32)
                for token, value in enumerate(self.cc_vocab):
                    if token_continues_suffix(value, suffix):
                        words[token // 32] |= 1 << (token % 32)
                signed = [value if value < 2**31 else value - 2**32 for value in words]
                self.cc_masks[suffix] = torch.tensor(signed, dtype=torch.int32)
            selected = self.cc_masks[suffix].to(bitmask.device)
            bitmask[idx, :len(selected)] &= selected

    class CCBackend(OriginalBackend):
        cc_view_protocol = PROTOCOL
        def compile_grammar(self, request_type, grammar_spec):
            result = super().compile_grammar(request_type, grammar_spec)
            if isinstance(grammar_spec, str) and '\n// ' + PROTOCOL + '\n' in grammar_spec:
                # Token bytes, rather than re-tokenized text, define the 512-token cap.
                vocab = [self.ll_tokenizer.decode_bytes([token]) for token in range(self.vocab_size)]
                return CCGrammar(result, vocab)
            return result
    native.GuidanceBackend = CCBackend


def endpoint_plugin():
    """Factory loaded only from the experiment's vllm.endpoint_plugins entry."""
    from .inference.native_state_service import RWKVNativeStateEndpointPlugin, RWKVNativeStateService

    class CCService(RWKVNativeStateService):
        def capabilities(self):
            value = super().capabilities()
            value['cc_view'] = {'protocol': PROTOCOL, 'think_limit': THINK_LIMIT,
                                'same_native_state_transport': True}
            return value

    class Endpoint(RWKVNativeStateEndpointPlugin):
        async def init_state(self, engine_client, state, args):
            state.rwkv_native_state = CCService(CCGrammarEngine(engine_client), args)
            await state.rwkv_native_state.initialize()
    return Endpoint()
