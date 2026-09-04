# Residual token/context rejection after projection v1

The first decision-state projection reduced rejected rows from 1,652 to 38 and
reduced the maximum from 9,198 to 2,723 exact RWKV tokens. Mean length fell from
3,360.33 to 1,566.03 tokens. All 38 residuals were final cumulative-coverage states.

The remaining overhead was non-semantic audit data repeated inside every projected
action (`action_id`, completed `status`, projection version, and artifact refs). These
values remain authoritative in the append-only ActionRecord/store. Projection v2
moves its version to the ledger root and keeps the ordered decision inputs only:
operation, normalized arguments, and bounded result.
