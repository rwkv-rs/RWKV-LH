# SEL-2P9 S39-S50 release result

## Outcome

The current direct architecture now has a separately deployed 2.9B Selector
and preserves the separate 13.3B Executor role. The Selector receives only the
compact V3 task/progress and the fixed 25 name/description classes, emits one
raw Hidden+MLP argmax, and owns its own recurrent checkpoint chain. Tool
arguments, tool execution, observations, and final prose remain outside this
Selector lane.

The released Selector uses the native zero state. S31 state tuning remains
rejected and inactive. The release does not claim that Selector state tuning is
unnecessary; it establishes the correct zero-state baseline before a later
fixed-data state ablation.

## Root cause sequence

- S35 showed that the old S34 Head was 98.6% on the selected current decision
  but only 64.44% on history prefixes. Product wire/state/runtime parity was
  correct; prefix supervision was missing.
- S36 added prefixes, but S37 held-out accuracy was only 93.07%.
- The audit found that S30 recomputed a different depth permutation per query
  and reused the train English source pool across splits.
- S38 fixed depth assignment and source partitioning, then exposed a remaining
  English coverage restriction from split-specific contract variants.
- S39 made all six variants eligible inside each already isolated source pool.
  No architecture, feature, loss weighting, threshold, or evaluation gate was
  changed.

## Fixed data and development selection

- Dataset: 2000/500/500 trajectories and 3428/857/857 prefixes for
  train/dev/test; 5142 total prefix rows.
- Dataset SHA-256:
  `b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`.
- Feature manifest: 5142 rows in 94 content-addressed GPU0 shards, generated
  without text sampling; SHA-256
  `b56e5cefab701128f7217bdecb00f2c1bd64b9505b8be61d9e55a1fc78c13481`.
- Fixed ascending capacity order selected the first candidate, `concat-h64`;
  h128 was not trained.
- S39 dev: 839/857 = 97.90%, macro F1 98.20%; history 96.92%, current
  98.60%, English 95.80%, Chinese 100%; S28 retention 750/750.
- Locked Head file SHA-256:
  `e2c4ffa85bb98637f8ba3dd2caf5789b732f2bb43ebc9b19bc4242e0ff3063dd`.
- Head hash:
  `73ecba1dcd84a2b8005d486b71fad210b1aab2f9981e8e04b2b7c90846ade7a7`.

## One-shot source-heldout S40

All preregistered gates passed on all 857 S39 test prefixes:

- accuracy 98.250%, macro F1 98.518%;
- history 98.319%, current 98.20%;
- English 96.737%, Chinese 99.766%;
- positions 0/1/2: 98.40%, 97.255%, 100%;
- every supported class recall at least 90%;
- every sibling boundary at least 95%;
- S28 retention 750/750 = 100%.

No test row was used for training, normalization, early stopping, capacity
selection, or thresholds. No additional RWKV forward, generated text,
postprocessing, fallback, tool execution, or Executor call occurred. Test report
SHA-256:
`aa8fe7d3973310d00b34294f8d3d043935fafc2fd0f20d51b15afee9ffcb12a8`.

## Real product S41

The local production client and `/v3/select` service replayed 25 current cases,
one per canonical class, and all 37 prefixes in their complete trajectories:

- 37/37 exact online labels;
- online/offline raw-logit maximum absolute difference: 0;
- current median latency: 94.5 ms; P95: 109.8 ms;
- all parent checkpoints, token positions, GPU0 identity, Head/model hashes,
  V3 bootstrap continuation, and explicit zero state matched;
- request wire contained no argument schemas, tool arguments, tool results, or
  Executor text;
- generation, sampling, output modification, retries, fallback, Harness tool
  execution, and 13.3B calls were all zero.

Canary report SHA-256:
`75ad2c9fa2d31ed57c69b4f53a3624985900e187604b354a64b335e1dbf647c5`.

## Product activation and systemic integration fix

`.env.local` now pins only the accepted Selector identity; the existing RWKV
Executor and Tavily values were preserved. The stable launch entry is
`scripts/run_network_selector_s39_zero_service.sh`, pinned to physical GPU0,
port 29621, the bundled engine revision, h64 Head, and zero profile. Dynamic
Selector states are stored separately under
`data/runtime/network-selector-s39-zero/dynamic-state`.

The first full regression correctly found that the old offline product Harness
hid `web_search` and `connector_lookup`, conflicting with the fixed 25-class
menu. The fix keeps both definitions visible only when the fixed independent
Selector is active, while the unchanged offline policy still rejects their
execution before any backend call. No class was deleted, no output gate was
relaxed, and no model output was changed.

Focused regression passed 45/45. Final project regression passed 520/520 with
one unrelated Python 3.13 multiprocessing deprecation warning. The structured
record is `run_s41_v3_product_shadow_canary/FULL_REGRESSION.json`.

## Live retrieval root cause and remediation

S42 correctly failed its Tavily-specific gate while the Harness still committed
six Bing-backed evidence records. Tavily authentication had succeeded on the
first configured credential and returned three results, so the credentials were
not deleted. The old provider counted three page failures but discarded their
causes.

S43 repeated the same query with the same frozen implementation and fetched all
three pages, proving that the query, key, provider API, SSRF policy, and page
formats were viable. S44 then added one bounded retry for explicit transient
transport failures plus secret-safe per-attempt diagnostics; policy failures are
never retried. S45 used those diagnostics to identify the actual local failure:
all six original-page attempts to `github.com` ended in `ConnectTimeout` or
`ReadTimeout`. Bing fallback still committed evidence, so the stable defect was
local direct-host reachability rather than routing, credentials, or RWKV output.

Tavily's documented `include_raw_content="markdown"` mode returns cleaned and
parsed page content separately from its optional generated answer. S46 verified
that the frozen query returned non-empty extracted content for 3/3 results in a
single API response. S47 therefore keeps independent public-page fetching as
the first choice, but after two eligible transient failures may commit the exact
provider-extracted bytes under the distinct source type
`tavily_extracted_public_web_page`. Generated answers and snippets remain
disabled and unused. Policy, DNS/public-address, peer, redirect, byte-bound,
permanent HTTP, empty, non-string, and over-1,000,000-byte failures cannot enter
this path. Extracted content is never described as original response bytes.

S49 splits connect/read bounds to 5/20 seconds and adds a per-search, per-host
circuit. The first result still gets a direct attempt and one retry. If both are
transient failures, later results on the same host receive a fresh public-URL
validation and may use the already typed extracted transport without repeating
socket timeouts. Circuit state is not shared across searches or users, and a
different host still gets its own direct attempt. The preregistered S48 live run
was never started and is preserved as explicitly superseded before execution.

## Final live S50 acceptance

The one-shot real product-Harness run passed every frozen gate:

- exact fixed 23-operation executable menu and unchanged `AUTO_PUBLIC` policy;
- first Tavily credential authenticated successfully; 3/3 pages committed;
- no Bing or DuckDuckGo fallback;
- 31.400 seconds against a preregistered 60-second limit;
- two unavailable hosts opened request-local circuits, with one later same-host
  socket attempt skipped after fresh public-URL validation;
- nine exact-span evidence records, all explicitly typed and transported as
  `tavily_extracted_public_web_page` / `tavily_extracted_markdown`;
- every extracted-content SHA-256 matched its immutable raw snapshot/source
  record ID, and every record matched the outer Tavily response hash/request ID;
- 10 immutable raw, clean, manifest, and route files; no configured credential
  in results or snapshots;
- one Harness action; zero agent retries, alternative-tool fallbacks, Selector
  calls/postprocessing, Executor calls, RWKV generations, or RWKV-output
  modifications.

S49 focused retrieval tests passed 34/34, related retrieval/Harness/Selector
release tests passed 81/81, and the final project suite passed 533/533 with the
same unrelated Python 3.13 fork deprecation warning. S50 acceptance report
SHA-256:
`a7bb81fcb4d6a5281af801843adcb57f548bd1185ca579b43b1e98f496af343b`.

The stable Selector remains healthy on physical GPU0 with the exact S39 h64
Head, V3 input/fusion protocol, and explicit zero state. Networking changed only
the retrieval backend; Selector/Executor separation, their state boundaries,
the fixed tool classes, and original RWKV outputs remain unchanged.
