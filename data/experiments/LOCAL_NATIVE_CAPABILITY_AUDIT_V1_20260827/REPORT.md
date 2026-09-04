# RWKV-LH local-native capability audit v1

## Scope

This audit evaluates only the current `/home/chase/GitHub/RWKV-LH` product
paths. The earlier ECRA-derived route benchmark is retained as historical
evidence but is not used as a capability or state-selection gate here.

- Source commit: `ca1c4c856d6a4616db8d3856966dfb8c0443922e`
- Evaluated main state: Stage7 step 2000,
  SHA-256 `38f018eb5c7d8285428d5046365a4b0cbf325109a2d8d264112018ab4dfd5bc7`
- Main runtime: remote 13.3B vLLM-RWKV reached through local port 29610.
- Audit script SHA-256:
  `78f0044c7e24c2f527fe36960a3f3748d63d9e7019b02624ffb39b1c5c0d2ea0`.
- Trace summary script SHA-256:
  `0e7d3f8cfb94c26950d9dcfb49f1637f38b327980501261ca44ffe2dc39130ba`.

## Results

| Capability | Live result | Product judgment |
| --- | --- | --- |
| Main RWKV inference | Correct model completed a real generation in 0.98 s | Real and usable |
| Default one-command model binding | Health returned available, but real completion returned HTTP 404 because configured Stage1 model differed from served Stage7 model | Broken deployment contract |
| Direct Controller | RWKV selected `write_json`, `read_json`, then exact Final; completed in about 5 s | Real and usable for bounded tasks |
| Local tools | File write/read, text search, sandboxed command, and calculator executed successfully | Real and usable |
| Autonomous public web | RWKV selected `web_search`, fetched `https://example.com`, committed exact evidence, and answered `Example Domain` | Real and usable for the tested exact-URL path |
| Local-only under `auto_public` | RWKV selected `read_file`; no network action occurred | Real for the tested boundary |
| Structured public lookup | RWKV selected `connector_lookup(package_release, requests)` and the first provider request succeeded | Real but narrowly scoped |
| Network policy | A synthetic secret-shaped query was rejected before network execution | Real and fail-closed for the tested case |
| Immutable retrieval recovery | A committed `web_search` route was recovered without provider replay | Real |
| Strong Supervisor transport | `/models` and actual chat-completion readiness succeeded; observed latency ranged from about 7 s to 51 s | Real but high/variable latency |
| Contract Graph | Tool atoms wrote and verified the requested JSON, but the parent run interrupted on an unprovable final-wording obligation | Not reliable as a general default |
| Proactive queue | SQLite enqueue, fenced claim, Controller execution, completion, and notifications all succeeded | Real; persistent worker was not running before the audit |
| Web UI | Local HTTP create/run/status path completed a real `read_file` Controller task when bound to the served model | Real; normal launch inherits the broken default model binding |
| 0.4B State Router | Persistent service answered and emitted immutable shadow logs; tested request took 13.14 s and abstained while main RWKV correctly chose local | Experimental only; no routing authority |
| Native RWKV session state | Runtime still declares prompt replay; no create/resume/fork/export/import durable recurrent-state contract | Not implemented |

## Confirmed defects

1. **Model identity is not part of health.** `rwkv-lh-stack status` and the Web
   health endpoint reported `available=true` while the configured model was
   absent. A subsequent default completion failed with HTTP 404.
2. **Contract Graph mixes execution and presentation obligations.** A simple
   request was fully executed and read back, but `concise confirmation` was
   encoded as an obligation requiring result-capsule evidence. A redundant
   correction produced another read and candidate confirmation, then duplicate
   correction fencing interrupted the run.
3. **Parent Contract Graph status is incomplete.** Product status showed zero
   actions and zero model requests although atom events recorded successful
   `write_json` and `read_json` calls.
4. **Egress provenance precedence is wrong after retrieval.** The public user
   literal `requests` was accepted on the first connector call. After the
   provider output also contained that word, identical calls were labeled as
   tool-untrusted and policy-rejected. User-public literals must be resolved
   before incidental matches in prior tool text.
5. **RWKV repeats after sufficient evidence.** After a successful package
   lookup, the model selected the same connector three more times before
   finalizing. This is a state/data problem after the provenance bug is fixed.
6. **Connector naming overstates capability.** The implementation is a small
   public read-only catalog for GitHub, PyPI, Crossref, and Open-Meteo. It is not
   an authenticated account connector layer. `github_code` and
   `weather_alerts` are advertised but deterministically unavailable.
7. **State Router is not product-ready.** The live shadow added about 13 s and
   abstained on a simple local route. It must remain non-authoritative.
8. **State tuning is global initial-state tuning, not per-run durable state.**
   Every new request receives one fixed 61-layer WKV initial state. Conversation
   continuation is reconstructed through prompt replay.

## Recommended architecture

1. Keep separate processes but make one project-owned deployment profile the
   authority for service unit, endpoint, served model, base/state hashes, and
   runtime features. Mark health unavailable unless the expected model is in
   `/models` and a bounded completion smoke succeeds.
2. Keep direct RWKV as the default. Invoke the strong planner only for explicit
   complex multi-stage requests or a conservative complexity/risk gate.
3. Split Contract Graph obligations into `executable_observation` and
   `presentation_constraint`. Only the former participates in evidence closure;
   the latter is checked on the final RWKV text and can never schedule a tool
   correction.
4. Project atom attempts/actions/model calls into the parent product status and
   UI without creating a second mutable truth.
5. Fix provenance precedence and register only connector operations backed by
   an available provider. Rename the current tool to
   `public_structured_lookup` unless an authenticated provider registry is
   actually implemented.
6. Leave the 0.4B Router disabled after collecting its diagnostics. For the
   first product version, use the tuned 13.3B RWKV itself for tool/network
   selection plus a mechanical Network Gate.
7. Train the next state round only from local product traces: successful
   evidence followed by stop, policy rejection followed by safe recovery,
   local-first under `auto_public`, and exact web-versus-structured-source
   boundaries. Re-evaluate on real Controller runs, not borrowed route labels.
8. Add native recurrent-state create/resume/fork/export/import only after the
   inference scheduler can isolate state per run and attest its identity. Until
   then, document prompt replay honestly and do not call it durable RWKV state.

