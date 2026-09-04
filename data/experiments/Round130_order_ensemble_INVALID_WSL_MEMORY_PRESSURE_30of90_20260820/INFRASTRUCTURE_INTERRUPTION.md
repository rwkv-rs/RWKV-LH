# Round130 infrastructure interruption — concurrency 2, 30/90

**Disposition:** INVALID / CLOSED. This directory is not an official Round130 result and must not be
scored, resumed, or combined with another run.

The concurrency-2 attempt persisted 30/90 results before closure: 22 completed, 7 interrupted, and
1 result reported as running. Two additional case workspaces existed but had not produced a persisted
suite result.

The local process pool reused each worker across many cases. A long-running worker retained memory
from earlier cases and the unit reached approximately 15.8 GB resident memory plus the full 8 GB WSL
swap allocation. Both worker processes entered the memory-cgroup high-pressure wait path. E2E-H05
stopped writing durable state after 2026-08-19 15:06 CST; E2E-LH02 still made very slow progress, with
roughly one checkpoint every 30–70 minutes. Continuing under that pressure no longer provided a
credible path to completing the frozen Full90.

The unit was stopped explicitly on 2026-08-20 before the successor run. Memory immediately returned
to approximately 2.2 GB used and swap returned to zero, confirming that the retained worker heaps were
the local pressure source. The artifacts remain only as infrastructure evidence. No partial metric is
used for KEEP, REVERT, R132 ingredient selection, or terminal-threshold decisions.
