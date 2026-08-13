# Round43 Canary Causal Analysis

## Result

- Fixed canary set: `E2E-B04`, `B05`, `B06`, `B08`, `B11`, `B12`, `B13`, `B18`, `B27`, `B29`.
- Agent completed: `1/10`.
- External acceptance: `8/10`.
- Strict E2E: `1/10`.
- Only `E2E-B27` completed and passed external acceptance.
- Known false-positive cases `B04` and `B29` were blocked, but all seven externally correct controls (`B05`, `B06`, `B08`, `B11`, `B12`, `B13`, `B18`) were also blocked.

## Chain-level attribution

Round43 retained the Round41 criterion-local source selection and added a second focused RWKV audit only after an initial pass. The audit received the fixed criterion, the already selected actual and expected references, their full stored observations, and the initial reason. It could only confirm or request replan.

The new stage did not merely remove incorrect passes. It converted every correct control in the canary into a false negative. The common failure begins at the interface between the Goal criterion and the second audit: many criteria are established by the complete causal frontier or by a typed property of an observation, while the audit is forced to decide from one selected pair as though that pair were a self-contained equality proof. Once the audit rejects that incomplete projection, the Controller correctly commits no Goal evidence and the run is blocked. The downstream block is therefore an amplification of an upstream representation mismatch, not evidence that the produced workspace is wrong.

The sequence is:

1. Task planning, action execution, task-local validation, and external workspace result are correct for seven controls.
2. Round41's initial criterion-local decision selects a permitted source pair and proposes pass.
3. Round43 projects the criterion onto only that pair and asks for a second content judgment.
4. The focused audit treats absence of a complete standalone comparison in the pair as insufficient evidence.
5. The Controller atomically rejects Goal completion, producing seven false negatives.

For `B04` and `B29`, the same conservative audit happened to suppress known incorrect workspaces. That does not make it a valid general mechanism: its selectivity is `0/7` on the correct controls in this canary. It is a broader rejection gate, not a better Goal-evidence interface.

## Architectural conclusion

- Do not add another semantic audit or comparison call after RWKV's criterion decision.
- Do not move this judgment into the protocol format converter. The converter remains limited to lossless mapping of registered wire forms into one canonical internal shape.
- The next change must improve the information boundary itself: stored observations should be projected into explicit, lossless fields (observed path, observed content/value, completeness, digest, metadata) instead of asking RWKV to infer those fields from truncated serialization envelopes.
- The Controller may validate references, ownership, lineage, completeness, and schema mechanically, but must not select the answer or reinterpret RWKV's pass/replan decision.

Round43 was stopped after the preregistered canary. No Basic30 run was performed. The Round43 code was reverted to the Round41 implementation and is not eligible for upload.
