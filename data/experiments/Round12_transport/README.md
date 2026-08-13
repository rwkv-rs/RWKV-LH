# Round12 formal durable transport

## Source and purpose

- Source: raw OpenAI-compatible request/response bytes transported without semantic parsing between
  the frozen local RWKV-LH runtime and the unchanged remote vLLM RWKV endpoint.
- Version: `rwkv-generation-spool.v1`.
- Purpose: preserve exactly-once model invocation and byte-identical response delivery across an
  unstable public SSH path during the independent Round12 formal run.
- Remote formal job root:
  `/home/chase/rwkv_lh_transport/round12_formal_20260812T125000Z`.
- Local proxy audit: `formal_proxy_audit.jsonl`.
- Remote spool SHA-256:
  `461b647e60d84dd5d75e0b4fb3556bf6e4e6108dd854180c6ac92e72689d34ae`.
- Local proxy SHA-256:
  `ac6912c2ee03686efeea16a85f8be7afdad87e701867f10b0f82d3c4b94efedd`.

## Generation

The remote spool persists each unique job request, calls localhost vLLM once, and persists the raw
response. The local proxy may reconnect only to retrieve the same job response. Different legitimate
calls always receive different job ids even when their request bytes are identical. Neither layer
reads benchmark reference answers or acceptance rules, parses model answer semantics, retries model
generation, or changes response bytes.

If retrieval of an already-created job exhausts its deadline, the proxy returns HTTP 424. That
status is outside the frozen runtime's retryable set, preventing a client retry from allocating a
new job and invoking RWKV again when the first outcome is already persisted but temporarily
unreachable.

The formal runner uses `RWKV_READ_TIMEOUT=900` so the same persisted response can be retrieved after
network recovery. Model, sampling, max tokens by request type, context length, concurrency, Controller,
and evaluation remain frozen.

After the run, a metadata-only manifest will record job state, request/response byte hashes,
invocation counts, transport attempts, and exact correspondence to local model-request events. Raw
request/response content is already preserved by the per-case Round12 audit/model trace and is not
used by the transport gate to judge correctness.
