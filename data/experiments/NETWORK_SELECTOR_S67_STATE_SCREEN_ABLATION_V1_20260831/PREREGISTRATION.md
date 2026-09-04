# S67 state-screen head/geometry ablation preregistration

## Timing and purpose

This diagnostic is frozen after `S67-ST500` was rejected by the already registered h128 screen and before any ST1000/ST1500/ST2000 screen metric was read. It cannot select or release a product candidate and cannot change the S67 state protocol. Its sole purpose is to attribute a screen failure to head capacity, feature geometry, or train/dev generalization.

## Frozen inputs and isolation

- Dataset: `data/datasets/rwkv_lh_network_selector_v2_contract_s67_v1/cases.jsonl`, SHA-256 `0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859`; manifest SHA-256 `0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46`.
- Feature candidates: zero state and numbered S67-ST500/ST1000/ST1500/ST2000 mean+last manifests produced by the frozen extractors. Only train 2000 and dev 500 are parsed. Test 500 remains skipped before JSON parsing.
- Label order remains `NETWORK_EXACT_TOOL_LABELS`; no family remap, rule gate, mask, post-hoc repair, class merge, or threshold route is allowed.
- No RWKV text generation or sampling is invoked. Raw hidden and logits are not modified, dropped, reordered, repaired, or replaced.

## Fixed heads and optimization

Every available state is evaluated with all four heads on the same concatenated 5120-d mean+last feature and train-only mean/std:

1. `H128`: one Linear(5120,128), GELU-tanh, LayerNorm, dropout 0.05, Linear(128,25). This exactly repeats the registered screen structure.
2. `H256`: the same structure with hidden 256.
3. `H2X128`: Linear(5120,128), GELU-tanh, LayerNorm, dropout 0.05, Linear(128,128), GELU-tanh, LayerNorm, dropout 0.05, Linear(128,25).
4. `LINEAR`: Linear(5120,25) only.

All use seed 1067, AdamW learning rate `1e-3`, weight decay `1e-4`, batch 256, cosine schedule, at most 160 epochs, gradient norm 1.0, and patience 30. The selected epoch maximizes the lexicographic tuple `(minimum of accuracy/0.96, macro-F1/0.96, minimum-recall/0.90; accuracy; macro-F1; -epoch)` on dev, identical to the screen. This is diagnostic model selection, not product selection.

## Fixed metrics and geometry

- Report train and dev accuracy, supported macro-F1, minimum supported recall, full 25x25 confusion, and per-label precision/recall/F1.
- The unchanged reference gates are accuracy `>=0.96`, macro-F1 `>=0.96`, and every supported-label recall `>=0.90`.
- For each state versus zero, compute row-aligned feature drift on the 500 dev rows: mean cosine similarity `mean((x·y)/(||x||2||y||2))` with denominator clamped to `1e-12`; mean relative L2 `mean(||x-y||2 / max(||y||2,1e-12))`; and mean absolute delta. Features remain float32 and are not normalized for these drift measurements.
- Generalization gap is train metric minus dev metric for the selected checkpoint. The ten largest off-diagonal dev confusion counts are reported without manual regrouping.

## Attribution rules

- If an alternate neural head passes all three gates where H128 fails, the observed bottleneck is head capacity/geometry for that state; this does not authorize release without the original registered cascade gates.
- If train passes but dev fails, the observed bottleneck is state/data generalization.
- If no fixed head passes on dev, the state/prompt/data objective remains the bottleneck; thresholds and evaluation are not changed.
- No S67 locked-test, retention dataset, Harness canary, or product profile is opened by this diagnostic.
