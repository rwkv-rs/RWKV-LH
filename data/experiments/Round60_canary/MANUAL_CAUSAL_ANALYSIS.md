# Round60 fixed-15 manual causal analysis

## Frozen outcome

- Strict E2E: `4/15`
- External acceptance: `4/15`
- Agent completed: `4/15`
- FP: `0`
- FN: `0`

Round60 fixed B01, M03, and M12 failure modes from Round59, but remained below the uploaded Round46 same-case Strict result. It is not upload-eligible.

## Manually verified causal changes

- **B01**: action output and runtime metadata are now distinct fields. The exact trailing newline remains in observed content and the case becomes Strict.
- **M03**: Task-local causal closure excludes the obsolete earlier `legacy_note` version. The current migrated JSON is adjudicated instead of being confused with an older observation.
- **M12**: the implementation and test observations are passed through the final Task's causal dependency closure, avoiding the full-history hallucination that changed division into multiplication.
- **M01 regression**: adding `advances_criteria` and `satisfies_criteria` to the main Task-batch protocol perturbed planning. RWKV omitted the prerequisite per-file reads and overwrote service JSON from guessed partial structures, losing unrelated fields.
- **LH02 regression**: every planned Task returned empty `satisfies_criteria`, so no Task-local commit ran. The system fell back to the same long full-history rescan and still failed the final verification criterion.
- **Negative cases**: the new local handoff did not introduce FP/FN in the fixed set, but this came partly from empty Task bindings and therefore did not demonstrate a reliable Goal-effect protocol.

## Root cause and next step

Task execution planning and Task-to-Goal classification should not share one wide schema. Criterion arrays in the planning response change the weak model's execution plan and are often left empty. Restore the five-field Task protocol and ask RWKV for Goal effect only after a real Task observation exists.
