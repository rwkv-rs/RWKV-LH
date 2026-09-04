# EXE-G3/G6 request-profile engine preregistration

Frozen on 2026-08-29 (Asia/Shanghai), before G6 checkpoint evaluation or
selection. This is the deployment gate after dedicated-process Stage B; it does
not authorize activating a G6 candidate that fails the earlier gates.

## Architecture

Patch a versioned copy of the pinned local `vllm-rwkv` source; do not alter the
currently serving source tree or port 18070. The copied engine preloads exactly
the selected G3 and selected G6 content-addressed WKV states plus native zero.
The manifest default remains zero. Every product request explicitly supplies a
registered `(profile_id, state_sha256)` pair through `vllm_xargs`.

`retrieval.mode == offline` binds G3 once when the task/controller is created.
Any immutable `retrieval.mode != offline` binds G6 once. This is a mechanical
policy-field decision, never a keyword or model route. The chosen immutable
settings object is reused by the main Executor and every atom created for that
task. There is no stage-level state selection or state switch. S60 remains a
separate 2.9B zero-state Selector.

If the network profile pair is missing, incomplete, malformed, or request-state
delivery is unavailable, network-task controller construction fails closed.
The Resolver, vLLM extension, and Harness never repair, rank, rewrite, truncate,
delete, or replace RWKV output.

## Engine isolation gates

1. The copied engine source inputs and outputs, profile module, manifest, both
   state files, model artifact, launch command, physical GPU0, and server log
   are content-addressed and recorded.
2. Requests with only an ID, only a digest, an unknown ID, or a wrong digest are
   rejected before recurrent-state row allocation. Registered G3, G6, and
   explicit zero requests succeed.
3. Use all 72 frozen G6 dev `protocol_rejection_recovery` prompts. Run two
   sequential orders at concurrency one: `G3 then G6` for every prompt, followed
   by `G6 then G3` for every prompt. Sampling is temperature 0.1, top-p 1,
   top-k 0, seed 1067, one request and first raw output only.
4. For each profile, canonical-exact pass/fail by sample must equal its
   dedicated-process ablation result in both orders. The two orders must also
   produce byte-identical raw text per `(profile, sample)`; any order dependence
   or cross-profile contamination fails. G6 must retain the preregistered
   positive net recovery gain over G3.
5. Report multi-profile latency against the corresponding dedicated-process
   recovery rows. A latency regression does not permit changing quality gates
   or outputs; it is a deployment-blocking performance defect if median exceeds
   1.25x or p95 exceeds 1.35x after excluding service startup.

## Product-path gates

First run a fresh process-attested G3+S60 Full90 control with the same code,
sampling, case order, and limits. Then, with the experimental multi-profile
service and S60:

- the frozen general Full90 uses request-selected G3 and must reproduce the
  control's per-case strict-pass and completion booleans exactly, with full
  raw/input/profile integrity; historical Round148 counts are reported only as
  context because it used a different architecture and are not substituted for
  this same-architecture control;
- frozen live V1 remains 2/2 and grounded V2 remains 6/6 using request-selected
  G6;
- retrieval quality remains 9/9 hard gates;
- every persisted task has one profile per lane and zero within-run switches;
- the existing port-18070 product service remains healthy throughout.

Only after all gates pass may the runtime profile resolver and multi-profile
service configuration become the local V1 default. If any gate fails, G3 remains
the default and G6 stays an unactivated diagnostic artifact.
