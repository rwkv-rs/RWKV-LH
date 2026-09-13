"""Select explicit RWKV transports without changing model output or credentials."""

from .native_rwkv import NativeRWKVClient, inspect_envelope


def model_client_class(settings):
    if settings.native_transport == "rwkvos_batch":
        from .rwkvos_batch import RwkvosBatchClient
        return RwkvosBatchClient
    return NativeRWKVClient


def model_client_options(settings, **overrides):
    options = {
        "base_url": settings.native_base_url, "model": settings.native_model,
        "timeout_seconds": settings.native_timeout_seconds,
        "context_window_tokens": settings.native_context_window_tokens,
        "max_concurrency": settings.native_max_concurrency,
    }
    if settings.native_transport == "rwkvos_batch":
        headers = {}
        for name, value in (
            ("CF-Access-Client-Id", settings.rwkvos_cf_access_client_id),
            ("CF-Access-Client-Secret", settings.rwkvos_cf_access_client_secret),
        ):
            if value.get_secret_value():
                headers[name] = value.get_secret_value()
        options.update(headers=headers, state_id=settings.rwkvos_state_id,
                       reader_state_id=(settings.rwkvos_binary_reader_state_id
                                        if settings.native_resolver_protocol == "binary_query"
                                        else settings.rwkvos_reader_state_id),
                       writer_state_id=settings.rwkvos_writer_state_id,
                       reader_prompt_protocol=settings.rwkvos_reader_prompt_protocol,
                       reader_input_layout=settings.rwkvos_reader_input_layout,
                       writer_prompt_protocol=settings.rwkvos_writer_prompt_protocol,
                       stop_tokens=settings.rwkvos_stop_tokens, prefill_mode=settings.rwkvos_prefill_mode,
                       count_input_tokens=settings.rwkvos_count_input_tokens,
                       input_token_limit=settings.rwkvos_input_token_limit,
                       batch_size=settings.rwkvos_batch_size,
                       batch_wait_ms=settings.rwkvos_batch_wait_ms)
    else:
        options["api_key"] = settings.native_api_key
    options.update(overrides)
    return options


def model_answer_bounds(raw_text, trace):
    """Interpret the transport's explicit body bounds; never repair raw text."""
    if not isinstance(raw_text, str):
        return None
    transport = trace.get("transport", "native")
    if transport == "native":
        return inspect_envelope(raw_text, trace.get("prefill", "<think"))
    if transport != "rwkvos_batch":
        return None
    envelope = trace.get("envelope")
    if not isinstance(envelope, dict) or envelope.get("valid") is not True:
        return None
    span = envelope.get("answer_span")
    if not isinstance(span, dict) or span.get("unit") != "unicode_code_points":
        return None
    start, end = span.get("start"), span.get("end")
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(raw_text) or not raw_text[start:end].strip()):
        return None
    return start, end
