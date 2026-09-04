# Invalid provisional binding analysis

This provisional analysis is invalid and is retained only for auditability.

The first checker compared `ToolSelectionHandoff.consumed_decision_id` against
every Executor semantic-repair decision that inherited the same selection.  A
selection is consumed exactly once; later repair attempts correctly carry
`selection_consumption_decision=false` and have their own decision IDs.  The
checker therefore reported 13 false binding drifts even though operation,
selection, action, contract, and the one true consumption decision remained
exact.

No source run, audit, database, RWKV output, threshold, or preregistered gate
was changed.  The corrected content-addressed analysis is written to a new
directory and validates the one-time consumption binding separately from
inherited semantic-repair decisions.

