# Round13 标准答案与因果对比

90 题全部终止后才加载 hidden acceptance 与 Codex reference；它们未进入 Goal、plan、
action、witness、recovery 或 final prompt。系统没有改写、排序或替换 RWKV 输出。

| 指标 | Round12 | Round13 | 变化 |
| --- | ---: | ---: | ---: |
| Strict | 0/90 | 0/90 | +0 |
| External | 11/90 | 20/90 | +9 |
| Completed | 0/90 | 0/90 | 0 |
| FP | 0 | 0 | 0 |
| FN | 11 | 20 | +9 |

Round13 将 External 从 11 提高到 20，但 Strict 与 Completed 都仍为 0；因此只是动作/产物可达性
改善，不是完整 Agent 成功，也不满足 GitHub 晋级门。

## 终止原因与标准结果交叉

| 终止原因 | 题数 | External 正确 | External 错误 |
| --- | ---: | ---: | ---: |
| obligation_replan_contract | 34 | 10 | 24 |
| action_argument_contract | 14 | 0 | 14 |
| action_recovery_budget_exhausted | 11 | 0 | 11 |
| run_blocked_other | 10 | 5 | 5 |
| unhandled_priority_type | 8 | 5 | 3 |
| goal_parse_contract | 5 | 0 | 5 |
| planning_contract | 4 | 0 | 4 |
| recovery_analysis_contract | 3 | 0 | 3 |
| action_choice_contract | 1 | 0 | 1 |

## 逐题标准答案

所有 case 的 final 都为空，final-reference similarity 为 0。下面的有效比较是外部验收、
artifact similarity 与 score-independent lifecycle 原因。

| Case | 组 | External | 终止原因 | Artifact similarity | 标准答案 |
| --- | --- | --- | --- | --- | --- |
| E2E-B01 | basic | FAIL | action_recovery_budget_exhausted | — | greeting.txt is exactly Hello, RWKV-LH! followed by one newline. |
| E2E-B02 | basic | PASS | obligation_replan_contract | 1.000000, 1.000000 | report.json contains exactly project Orion and doubled_count 14. |
| E2E-B03 | basic | PASS | obligation_replan_contract | 1.000000 | config.json preserves name alpha and retries 4 while setting feature enabled true and mode safe. |
| E2E-B04 | basic | PASS | run_blocked_other | 1.000000 | archive/2026/source.txt is byte-equal to source.txt and archive/manifest.txt records its relative path. |
| E2E-B05 | basic | PASS | run_blocked_other | 1.000000 | app.env contains name demo, port 8080, and mode prod in original order with deprecated=true removed. |
| E2E-B06 | basic | PASS | obligation_replan_contract | 1.000000 | combined.txt is alpha, beta, separator ---, gamma, delta, with one final newline. |
| E2E-B07 | basic | PASS | unhandled_priority_type | 1.000000 | Production selects endpoint.txt containing https://api.example.com and no staging output exists. |
| E2E-B08 | basic | PASS | obligation_replan_contract | 1.000000 | manifest.json has exactly file=payload.txt and the lowercase SHA256 of payload.txt bytes. |
| E2E-B09 | basic | FAIL | action_recovery_budget_exhausted | — | stats.json is row_count 3, total_score 45, average_score 15. |
| E2E-B10 | basic | FAIL | action_argument_contract | — | slugify is implemented without NotImplementedError and all test_slug.py unittests pass. |
| E2E-M01 | medium | FAIL | obligation_replan_contract | 1.000000, 0.794595, 0.786737, 1.000000 | All three services are version 2.0.0 on stable runtime and summary maps each name to 2.0.0. |
| E2E-M02 | medium | FAIL | action_argument_contract | — | calculator.py is repaired without changing tests and the complete calculator test file passes. |
| E2E-M03 | medium | FAIL | goal_parse_contract | 0.466289 | users.json is schema 2 with two migrated records, display_name/status fields, preserved tags, and no legacy_note. |
| E2E-M04 | medium | FAIL | obligation_replan_contract | 1.000000, 0.825501 | Nebula 3.4.2 dated 2026-08-09 is recorded consistently in release.json and RELEASE.md. |
| E2E-M05 | medium | FAIL | run_blocked_other | 0.007272 | implementation_plan.md lists transactional state, no-repeat resume, and observable verification in that order. |
| E2E-M06 | medium | FAIL | goal_parse_contract | — | package contains only alpha.dat, gamma.dat, and a correct digest manifest; beta.dat is absent. |
| E2E-M07 | medium | FAIL | obligation_replan_contract | 0.234404 | resolved.json recursively merges defaults and overrides to localhost, port 9000, both features true, workers 4, source merged. |
| E2E-M08 | medium | FAIL | recovery_analysis_contract | 0.674334 | STATUS.md lists api, web, worker sorted with their latencies and Overall healthy. |
| E2E-M09 | medium | FAIL | action_argument_contract | — | Python calls use new_api, comments and strings retain old_api text, new_api doubles values, and discovery tests pass. |
| E2E-M10 | medium | FAIL | action_argument_contract | — | resilient.txt is recovered by RWKV with newline after observed transient failures and at least one replan. |
| E2E-H01 | hard | FAIL | action_recovery_budget_exhausted | — | records functions pass all tests and example_summary is count 3, total 10, by_name A 5 and B 5. |
| E2E-H02 | hard | FAIL | action_argument_contract | — | aggregate.json includes every shard exactly once with exact counts, value total, and category sums. |
| E2E-H03 | hard | FAIL | obligation_replan_contract | — | Six stages progress origin through \|1\|2\|3\|4\|5\|6 and resume never repeats completed attempts. |
| E2E-H04 | hard | PASS | obligation_replan_contract | 1.000000 | safe/result.txt is scope preserved with newline, stolen.txt is absent, and no scope violation occurs. |
| E2E-H05 | hard | FAIL | action_argument_contract | 0.157221 | priority_summary maps only the three PRIORITY yes filenames to their second-line signals. |
| E2E-H06 | hard | FAIL | obligation_replan_contract | 0.626525, 0.719430, 0.644065, 0.762001 | dev, stage, prod migrate to schema 3 storage dsn/pool_size with unrelated fields preserved and sorted report. |
| E2E-H07 | hard | FAIL | action_recovery_budget_exhausted | — | Queue priority and duplicate behavior pass full tests and VERIFIED.txt contains the successful OK summary. |
| E2E-H08 | hard | FAIL | action_recovery_budget_exhausted | — | ledger event_ids are evt-3, evt-1, evt-2 with count 3 and completed resume is byte-stable. |
| E2E-H09 | hard | PASS | obligation_replan_contract | 1.000000 | selected.json preserves backup payload and selected_source is data/backup.json after observing primary failure. |
| E2E-H10 | hard | FAIL | action_recovery_budget_exhausted | — | Inventory items are A1 18.0, B2 18.0, C3 4.5, grand total 40.5; report agrees and verifier passes. |
| E2E-LH01 | hard | FAIL | action_argument_contract | — | Pipeline fixes normalize, validate, price, build in staged order; release has alpha 6, beta 5, total 11 and verifier passes. |
| E2E-LH02 | hard | FAIL | action_argument_contract | — | Fifteen checkpoints preserve all five immutable constraints and final config adds generated_by RWKV-LH. |
| E2E-LH03 | hard | FAIL | obligation_replan_contract | 0.138884 | Recursive catalog index contains east, north, south with exact manifests/files/counts and total_records 10. |
| E2E-LH04 | hard | FAIL | obligation_replan_contract | 0.467728 | Event ledger deduplicates E1/E2/E3, count 3, total 13 and survives post-effect crash plus completed resume unchanged. |
| E2E-LH05 | hard | FAIL | planning_contract | — | All 20 shards use valid primary or fallback, exact sources/digests, recovered counts and value_total 630; report agrees. |
| E2E-LH06 | hard | FAIL | obligation_replan_contract | 0.171615 | Approved authority source wins with four ordered requirements; evidence cites it and rejects untrusted instructions. |
| E2E-LH07 | hard | FAIL | obligation_replan_contract | 0.767603 | Eight services migrate to schema 3 stable v3 including special storage/security migrations; report and compatibility verifier pass. |
| E2E-LH08 | hard | FAIL | planning_contract | 1.000000, 0.880000, 1.000000 | Keep b.reserve 70, roll back a.limit to 10 and c.mode to safe; compensation records kept/rolled back and invariants pass. |
| E2E-LH09 | hard | PASS | run_blocked_other | 1.000000, 1.000000 | Mock API completes create-query-update-replay-finalize with stable ids; resource ready version 2, finalized true, one 503 and one duplicate. |
| E2E-LH10 | hard | PASS | obligation_replan_contract | — | mean and clamp pass tests, README documents both and command, and manifest hashes math_ops.py plus README within 35 actions. |
| E2E-LH11 | hard | FAIL | planning_contract | — | Five checkpoints capture two facts per phase and memory_summary lists F01-F10 with exact values/artifact paths. |
| E2E-LH12 | hard | FAIL | action_recovery_budget_exhausted | — | Mini project parser/analyzer/reporter pass tests; example report is count 3, unique 2, longest alpha; docs and six-file digest manifest exist. |
| E2E-B11 | basic | FAIL | recovery_analysis_contract | — | normalized_name.txt is exactly RWKV Long Horizon followed by one newline. |
| E2E-B12 | basic | FAIL | goal_parse_contract | — | stats.json has exactly count 5, sum 25, min -2, and max 9. |
| E2E-B13 | basic | PASS | run_blocked_other | 1.000000 | config deployment becomes cn-east with 5 retries while service, enabled, and owner remain unchanged. |
| E2E-B14 | basic | FAIL | obligation_replan_contract | 0.550482, 1.000000, 1.000000 | merged.txt concatenates left, a -- line, and right; both sources remain byte-unchanged. |
| E2E-B15 | basic | PASS | obligation_replan_contract | 1.000000, 1.000000 | colors.json contains the first-seen unique list blue, red, green and no other key. |
| E2E-B16 | basic | PASS | run_blocked_other | 1.000000 | app.env is exactly NAME=worker, PORT=9000, MODE=prod with comments and blank lines removed. |
| E2E-B17 | basic | FAIL | obligation_replan_contract | 0.617465, 1.000000 | active_users.json has sorted active_names Ada and Zoe and active_count 2. |
| E2E-B18 | basic | FAIL | run_blocked_other | 0.687184, 1.000000 | total.json records subtotal 80.0, discount 12.0, and total 68.0. |
| E2E-B19 | basic | PASS | unhandled_priority_type | 1.000000 | manifest.json identifies payload.txt and its exact lowercase SHA256 digest. |
| E2E-B20 | basic | PASS | obligation_replan_contract | — | is_even returns a boolean based on divisibility by two and all parity tests pass. |
| E2E-B21 | basic | FAIL | obligation_replan_contract | 0.000000, 0.000000 | category_totals.json is alpha 3, beta 6, gamma 1 with no extra keys. |
| E2E-B22 | basic | PASS | unhandled_priority_type | 1.000000 | TASKS.md has the Tasks heading and unchecked inspect, repair, verify items in order. |
| E2E-B23 | basic | FAIL | obligation_replan_contract | 0.267725 | selected.json uses data/backup.json and preserves value region eu, revision 4. |
| E2E-B24 | basic | FAIL | action_argument_contract | 0.662122 | sorted.log has unique sorted lines error m, info a, warn z; log.txt is unchanged. |
| E2E-B25 | basic | FAIL | obligation_replan_contract | 0.814716 | settings.json keeps demo and safe mode, sets retries 6, and adds enabled true. |
| E2E-B26 | basic | PASS | unhandled_priority_type | 1.000000, 1.000000, 1.000000, 1.000000 | output contains only a.txt=A, b.txt=B, and nested/c.txt=C, each with one newline. |
| E2E-B27 | basic | FAIL | action_recovery_budget_exhausted | 0.887353 | Every protocol=v1 occurrence in service.conf becomes protocol=v2 and all other bytes remain. |
| E2E-B28 | basic | FAIL | action_choice_contract | — | metrics.json has integer latency_ms 48, requests 120, and errors 3. |
| E2E-B29 | basic | PASS | obligation_replan_contract | 1.000000 | backup/source.txt equals source.txt and backup/manifest.txt records the source-to-backup mapping. |
| E2E-B30 | basic | PASS | unhandled_priority_type | — | normalize_name trims, lowercases, and hyphen-joins whitespace; all tests pass. |
| E2E-M11 | medium | FAIL | run_blocked_other | 1.000000, 1.000000, 1.000000, 1.000000, 0.454545 | Four services migrate to schema 2 stable while preserving ports/workers; summary maps names to ports. |
| E2E-M12 | medium | FAIL | action_recovery_budget_exhausted | — | safe_divide divides and rejects zero; median is nonmutating and correct for odd/even inputs; tests pass. |
| E2E-M13 | medium | FAIL | recovery_analysis_contract | — | sales summary has 4 rows, quantity 10, revenue 39.5, and region totals north 17.5, south 12, west 10. |
| E2E-M14 | medium | FAIL | run_blocked_other | 1.000000, 0.767948 | Comet 2.1.0 release artifacts use date 2026-08-12 and alphabetically sorted changes. |
| E2E-M15 | medium | FAIL | obligation_replan_contract | 0.919360 | docs/index.json lists three source files with exact line/byte counts and totals 3 files, 29 bytes. |
| E2E-M16 | medium | FAIL | unhandled_priority_type | 0.662117 | recovered.json contains ids 01-05 in order, using fallback for 02 and 04 and primary for the rest. |
| E2E-M17 | medium | FAIL | unhandled_priority_type | 1.000000, 0.746203, 0.775146, 0.680301 | All packages use api v2 and compatible true; package_matrix gives sorted dependency lists. |
| E2E-M18 | medium | FAIL | obligation_replan_contract | — | digest_map.json maps all three recursive inputs paths to their exact lowercase SHA256 digests. |
| E2E-M19 | medium | FAIL | action_argument_contract | — | access summary counts 6 requests, exact status/path frequencies, and error paths admin and items. |
| E2E-M20 | medium | FAIL | goal_parse_contract | — | parse_records trims fields, converts scores, ignores blanks, rejects duplicate ids, and all tests pass. |
| E2E-M21 | medium | FAIL | obligation_replan_contract | 0.281963 | merged_users has ids 1,2,3 sorted, source_b overrides id 3, and record_count is 3. |
| E2E-M22 | medium | FAIL | obligation_replan_contract | 0.808404 | Only region and replicas are applied; debug/owner are rejected and untouched in updated_config. |
| E2E-M23 | medium | FAIL | action_argument_contract | 0.045256 | dist contains the three exact declared files plus manifest.json listing their sorted paths and nothing else. |
| E2E-M24 | medium | FAIL | action_recovery_budget_exhausted | — | TaskQueue rejects duplicate ids and pops highest priority with ascending id tie-break; tests pass. |
| E2E-M25 | medium | FAIL | run_blocked_other | 0.101000 | CHANGELOG.md orders versions 1.3.0 then 1.2.0 and sorts add before fix within each. |
| E2E-M26 | medium | FAIL | obligation_replan_contract | 0.890299 | validation keeps records 0 and 3, rejects index 1 for invalid_id and index 2 for invalid_name/status, counts 2 and 2. |
| E2E-M27 | medium | FAIL | obligation_replan_contract | 0.946429 | Deterministic build order is core, api, docs, web, app with node_count 5. |
| E2E-M28 | medium | FAIL | obligation_replan_contract | 0.862105, 1.000000 | July logs move byte-exact to archive; August logs remain; report lists moved and kept filenames sorted. |
| E2E-M29 | medium | FAIL | obligation_replan_contract | 0.270237 | zh-CN translations override hello/save, fall back for bye/cancel, and list missing keys bye and cancel. |
| E2E-M30 | medium | FAIL | action_recovery_budget_exhausted | 0.790620 | Config migrates timeout to 3000 ms and retry_count to retries under schema 2; report records both renames and verifier passes. |
| E2E-H11 | hard | FAIL | goal_parse_contract | — | Pipeline normalizes/validates/totals/builds correctly; release sorts alpha 15 and beta 8 with grand total 23; verifier passes. |
| E2E-H12 | hard | FAIL | unhandled_priority_type | 0.428216 | aggregate.json accounts for every item in all 15 generated shards exactly once with exact totals by category. |
| E2E-H13 | hard | FAIL | planning_contract | — | Six phase checkpoints contain the expected priority filenames and final summary maps seven priority documents to signals. |
| E2E-H14 | hard | FAIL | obligation_replan_contract | 0.777811 | Recursive catalog index contains east, north, south with exact paths/counts and total_records 10. |
| E2E-H15 | hard | FAIL | action_argument_contract | — | Event-report modules pass tests; report is total 3 with INFO 2 and WARN 1; docs exist and six artifact digests are exact. |
| E2E-H16 | hard | FAIL | action_argument_contract | 0.904762, 0.666667 | Keep workers 8 and fast mode, roll back timeout to 30 and memory to 40; compensation and invariant verifier agree. |
| E2E-H17 | hard | FAIL | obligation_replan_contract | 0.656448 | ledger entries A4, B7, C2 are first-seen unique with count 3 total 13; interruption and completed resume never repeat work. |
| E2E-H18 | hard | FAIL | action_argument_contract | — | Release products are A1 27, M5 6, Z9 18 with total 51; report/verifier pass and digests cover both outputs. |
