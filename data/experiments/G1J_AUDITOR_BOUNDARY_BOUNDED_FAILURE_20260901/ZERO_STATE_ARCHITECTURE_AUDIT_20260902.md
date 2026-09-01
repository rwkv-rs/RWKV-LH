# G1J zero-State architecture and capability audit

Date: 2026-09-02. The reviewed architecture is:

- Strong model: Planner plus read-only Stage Checker;
- G1J 2.9B: one exact operation selection per action;
- G1J 13.3B Executor: parameters, code/content, and tool execution in one
  persistent action session;
- G1J 13.3B Auditor: independent role-pure session, no Executor WKV merge;
- only an RWKV `final_answer` accepted by the RWKV Auditor may complete a Goal;
- Selector, Executor, and Auditor State profiles are independent optional
  environment bindings; all runs in this audit use `zero`.

## Confirmed engineering defects and repairs

The audit found and repaired generic chain defects rather than case-specific
answers:

1. invalid Auditor output could strand one durable audit boundary and stop the
   Goal; the boundary now resolves as `protocol_invalid` without granting step
   or completion authority;
2. an Auditor `repair` verdict incorrectly invoked Strong replanning; action
   repair now continues the same RWKV step, while only Stage Checker repair may
   invoke Planner;
3. `final_answer` was available before the rolling plan completed; it is now
   exposed only at the evidence-complete Goal frontier;
4. read-only steps exposed workspace mutation tools; the Controller now
   compiles a side-effect-safe menu from each step;
5. latest-eight evidence projection discarded the only action covering an
   early read/write root; projection now retains the current boundary and the
   newest successful action covering each declared root;
6. benchmark slices were treated as terminal failures; the runner now resumes
   ordinary Goal checkpoints within one fixed total transition budget;
7. schema-valid but Controller-invalid Strong PlanPatches entered the cache;
   GoalPlan responses now enter the cache only after complete Controller
   validation, and cache identity removes random run/audit/review IDs while
   retaining every semantic input;
8. a Stage Checker repair could append work after an unchanged frontier; such a
   patch is now rejected, and failed candidates are validated on an isolated
   plan so semantic retry starts from the unmodified durable plan;
9. Stage Checker received unrelated action history and truncated the relevant
   verifier read; it now receives only accepted evidence for that stage.

The source regression is `787 passed, 1 warning` under WSL after all repairs.

## Real zero-State capability

No strict five-case score can be claimed because the Strong relay repeatedly
returned HTTP 429. Infrastructure-invalid runs are not converted into model
failures. The valid prefixes and infrastructure-clean cases nevertheless give
stable role diagnosis:

- engineering remediation worked: in L3, read-only `patch_json` selections fell
  from 41 to 0 and protocol rejections fell from 41 to 35;
- Selector remains the earliest capability failure in long trajectories: R13
  L3 repeatedly selected `list_directory`, while L4 selected `current_time` 39
  times and never selected `read_file`; L4 had only four protocol rejections,
  so formatting is not the primary cause;
- Executor can create coherent multi-file Python artifacts, but R18 L2 fails
  the observed verifier contract at its first assertion and repeatedly chooses
  the wrong test command parameters;
- Auditor often reaches the correct semantic verdict but is unstable on the
  exact six fields, legal evidence references, and completion judgment; the
  Controller catches these errors, at the cost of additional calls.

This is enough to define precise per-role correction datasets, but not enough
to claim the current zero-State system completes the fixed project ladder. The
State Tune gate is therefore: train only on valid RWKV boundaries after
upstream engineering validation, evaluate against the frozen real-project
suite, and keep a role State only when it improves strict project outcomes and
does not regress other fixed cases. Strong Planner/Stage Checker is never State
Tuned.
