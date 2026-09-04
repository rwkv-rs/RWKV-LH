# SEL-2P9-S35 full-prefix deployment audit preregistration

## Purpose

S34 established 98.6% exact accuracy on the 500 frozen S30 **current-row**
decisions and established exact product/offline logit parity in the V3 GPU0
shadow canary.  The canary also replayed 48 earlier trajectory prefixes as a
diagnostic and observed only 23 exact historical labels.  Inspection of the
frozen S30 generator confirms that these are real earlier Selector targets,
not incidental metadata.  S35 therefore audits every routed position before
any `.env.local` product activation.

This is a deployment-coverage audit, not a new blind claim.  The 500 current
labels were consumed by S34 and 48 historical labels were observed in the S34
canary.  No S35 result may be described as blind.

## Frozen identities

- Dataset:
  `data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1/cases.jsonl`
- Dataset SHA-256:
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`
- Split: all and only the 500 rows whose frozen `split` is `test`.
- Decisions: each row's ordered `history_selector_inputs`, followed by its
  `selector_input`; expected labels are the corresponding
  `expected_history_labels`, followed by `label`.
- Frozen counts: 500 trajectories, 495 historical decisions, 500 current
  decisions, 995 total deployed-prefix decisions.
- Model: `rwkv7-g1i-2.9b-vllm-v1`
- Model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Head: S34 `concat-h64`.
- Head file SHA-256:
  `fe97f9eed3e96a63efb4937fc79e884399585dca1af37aa224d4477e73a3410e`
- Head hash:
  `6e2553e41dca4a3d3402e3f99b919c2b767a23d3fc64cba0662a9744b264a41d`
- Input protocol: `rwkv-lh.exact-tool-selector-input.v3`.
- Feature protocol:
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`.
- State profile: explicit `zero`, SHA-256 equal to 64 zero characters.
- Profile manifest SHA-256:
  `706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47`.
- Engine revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`.
- Physical device: only GPU0 (`CUDA_VISIBLE_DEVICES=0`).
- Product endpoint: local `/v3/select`; no offline feature substitution.

## Frozen procedure

1. Refuse execution unless all frozen files, imported protocols, runtime
   identity, GPU selection, and output nonexistence checks pass.
2. Start every S30 test trajectory with no parent checkpoint.
3. Submit every historical input and then the current input through the
   unmodified production `NetworkExactToolSelectorClient`.
4. Preserve the returned 25 logits and raw argmax exactly.  Do not sample,
   postprocess, repair, retry, fall back, execute a tool, or call the Executor.
5. Require the production V3 render to be byte-identical to each frozen S30
   bootstrap/step and require an exact Selector checkpoint parent chain.
6. Record all 995 raw decisions before computing aggregate metrics.

## Frozen metrics

Use exact canonical-label equality.  Report:

- total accuracy and 25-class macro F1;
- historical-prefix and current-row accuracy;
- English and Chinese accuracy;
- accuracy at trajectory positions 0, 1, and 2;
- per-class support, precision, recall, F1, and confusion counts;
- the six already registered sibling boundaries from S34;
- raw-integrity, wire-contract, checkpoint-chain, and latency diagnostics.

No similarity metric, label normalization, semantic equivalence, or revised
denominator is permitted after execution.

## Acceptance gates

S35 passes only if all gates pass:

1. exactly 500 trajectories, 495 history decisions, 500 current decisions,
   and 995 total decisions are recorded;
2. total exact accuracy is at least 0.96;
3. 25-class macro F1 is at least 0.96;
4. history accuracy and current accuracy are each at least 0.96;
5. English and Chinese accuracy are each at least 0.95;
6. each present trajectory position (0, 1, 2) has accuracy at least 0.95;
7. each of the six S34 sibling-boundary groups has accuracy at least 0.95;
8. every canonical class with nonzero support has recall at least 0.90;
9. every request and response satisfies the V3 identity/wire contract, every
   checkpoint belongs to the Selector lane with the exact zero profile, and
   every row retains exactly 25 finite raw logits with no modification;
10. generation, sampling, postprocessing, retries, fallback, tool execution,
    and Executor calls are all zero;
11. model-startup-excluded median request latency is at most 3 seconds and P95
    latency is at most 5 seconds.

## Decision rule

- Pass: S34 may proceed to persistent local activation and broader Harness
  regression.
- Fail: `.env.local` activation remains locked.  Treat the result as a
  prefix-coverage/data-structure defect; construct a split-preserving,
  prefix-closed training set, train only on train prefixes, select capacity on
  dev prefixes, and evaluate with a separately frozen holdout.  Do not hide the
  defect with rules, retries, an Executor fallback, or changes to RWKV output.
