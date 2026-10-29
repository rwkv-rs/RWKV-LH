"""Reject unsupported RWKV sampling before upstream greedy normalization."""


def validate_rwkv_sampling(sampling):
    if not isinstance(sampling, dict):
        return
    for name, supported in (('min_p', 0.0), ('repetition_penalty', 1.0)):
        value = sampling.get(name)
        if value is None:
            continue
        try:
            valid = float(value) == supported
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError(f'RWKV Rapid-Sampling requires {name} == {supported}')


async def reject_unsupported_sampling(request, call_next):
    # Native State requests validate inside their journal transaction instead.
    paths = {
        '/v1/completions', '/v1/chat/completions', '/v1/chat/completions/batch',
        '/v1/responses', '/invocations', '/v1/completions/render',
        '/v1/chat/completions/render', '/v1/responses/render',
        '/inference/v1/generate',
    }
    if request.method == 'POST' and request.url.path.rstrip('/') in paths:
        try:
            body = await request.json()
        except ValueError:
            body = None  # Let the normal request schema report invalid JSON.
        if isinstance(body, dict):
            sampling = (body.get('sampling_params')
                        if request.url.path.rstrip('/') == '/inference/v1/generate'
                        else body)
            try:
                validate_rwkv_sampling(sampling)
            except ValueError as exc:
                from starlette.responses import JSONResponse
                return JSONResponse(status_code=400, content={'error': {
                    'message': str(exc), 'type': 'BadRequestError', 'code': 400}})
    return await call_next(request)
