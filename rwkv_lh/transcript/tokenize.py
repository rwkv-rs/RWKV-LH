"""Complete incremental-turn tokens and unshifted assistant-body supervision."""
import hashlib

from .parse import catalog
from .wire import END_OF_TURN_TOKEN_ID, HEADERS, PROTOCOL, render_turns


def segments(messages, native_tools):
    """(text, supervised) pieces in serving order.

    The host appends every header, including ``### Assistant``; the model
    generates only the assistant body. Each piece is encoded separately, as the
    serving append and the generated tokens are.
    """
    pieces = []
    for message, text in zip(messages, render_turns(messages, native_tools)):
        if message['role'] == 'assistant':
            header = HEADERS['assistant']
            pieces += [(message['role'], header, False), (message['role'], text[len(header):], True)]
        else:
            pieces.append((message['role'], text, False))
    return pieces


def tokenize_transcript(messages, *, tokenizer, native_tools, max_tokens=None):
    """Return complete input_ids/loss_mask, or reject a capacity overflow.

    Token merges cannot cross a piece boundary and accidentally supervise host
    bytes. Every assistant body is followed by one supervised end-of-turn EOS
    token, which the serving State also keeps; no BOS is added, no target is
    shifted, and no tail is dropped.
    This in-memory codec neither writes data nor authorizes training.
    """
    if max_tokens is not None and (type(max_tokens) is not int or max_tokens < 1):
        raise ValueError('positive token capacity required')
    catalog(native_tools)
    ids, mask, spans, rendered = [], [], [], []
    for role, text, supervised in segments(messages, native_tools):
        tokens = list(tokenizer.encode(text))
        if (any(type(token) is not int or token <= 0 for token in tokens)
                or tokenizer.decode_bytes(tokens) != text.encode('utf-8')):
            raise ValueError('tokenizer must preserve exact UTF-8 bytes without added special tokens')
        start = len(ids)
        if supervised:
            tokens.append(END_OF_TURN_TOKEN_ID)
        ids.extend(tokens)
        mask.extend([int(supervised)] * len(tokens))
        spans.append({'role': role, 'supervised': supervised, 'start': start, 'end': len(ids)})
        rendered.append(text)
    if max_tokens is not None and len(ids) > max_tokens:
        raise ValueError(f'transcript requires {len(ids)} tokens; capacity is {max_tokens}; no truncation')
    return {'protocol': PROTOCOL, 'input_ids': ids, 'loss_mask': mask, 'turn_spans': spans,
            'rendered_sha256': hashlib.sha256(''.join(rendered).encode('utf-8')).hexdigest()}
