The benchmark-local mock_api action is stateful. Reuse a request_id only for an exact retry. A 409 duplicate response means the original request was already applied.
