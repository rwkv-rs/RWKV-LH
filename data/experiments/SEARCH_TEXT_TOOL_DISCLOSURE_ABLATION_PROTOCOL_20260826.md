# Search-text tool-disclosure ablation protocol — 2026-08-26

## Question

Does the v2 canary interruption come from the progressive selector protocol rather
than from `search_text` execution or final-answer generation?

## Frozen comparison

- Control: `NATIVE-SEARCH-TEXT-RWKV-CANARY-V2-20260826`, progressive disclosure.
- Treatment: identical model, sampling, source tree, workspace, request, network
  policy, transition budget, and thresholds; change only
  `RWKV_TOOL_DISCLOSURE_MODE=full` under a new run id and state directory.

## Pre-registered metrics and thresholds

- Record run status, exact locator precision/recall/F1, highest-priority exactness,
  successful action count, protocol rejection count, model request count, and elapsed
  wall time.
- The treatment passes only if the original canary thresholds all pass; reducing
  rejections without correct completion and priority does not count as a pass.
- No prompt, fixture, expected order, sampling value, or metric may be changed after
  the treatment's first model request.
