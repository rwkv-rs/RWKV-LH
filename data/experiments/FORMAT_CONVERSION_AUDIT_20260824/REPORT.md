# RWKV 原始输出与格式转换层统计报告

日期：2026-08-24

## 结论摘要

- 固定主样本：90 个 case、1111 次 RWKV 返回；其中 53 个 case 有模型请求，37 个因计划不可用而为零请求。
- 当前 `direct-call-envelope.v1` 重放解析成功 1005/1111；SQLite 权威 decision 接受 957/1111、拒绝 154/1111。
- 原始 canonical `function+params` 为 397/1111；发生任意 model-I/O 转换 608/1111。
- 可观测格式救回（非 canonical envelope 或完整 Markdown fence）608/1111；其中最终通过 schema 587/1111。
- accepted response 中有 587/957 依赖 model-I/O 转换才能投影到 canonical call；canonical 且通过为 370/1111。
- accepted action 共 520 次；包含 registry default 在内发生参数转换 289/520，排除“仅默认值填充”后仍需显式接口转换 2/520。
- Trace 与 SQLite 共有 request 1111 个，原始输出逐字节相同 1111/1111；trace-only=0、DB-only=0。
- Trace candidate commit/rollback 与 SQLite accepted/rejected 一致 1111/1111。

## 原始表面格式

| 类别 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `bare_json_candidate` | 1111 | 1111 | 100.00% | 99.66%–100.00% |

首尾空白独立统计：0/1111（0.00%）。

## 调用信封格式

| 类别 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `alias_pair:function+arguments` | 592 | 1111 | 53.29% | 50.35%–56.20% |
| `canonical_function+params` | 397 | 1111 | 35.73% | 32.97%–38.60% |
| `invalid_envelope` | 103 | 1111 | 9.27% | 7.70%–11.12% |
| `alias_pair:function+parameters` | 11 | 1111 | 0.99% | 0.55%–1.76% |
| `alias_pair:function+function_args` | 5 | 1111 | 0.45% | 0.19%–1.05% |
| `invalid_json` | 2 | 1111 | 0.18% | 0.05%–0.65% |
| `invalid_single_key_call` | 1 | 1111 | 0.09% | 0.02%–0.51% |

### 各信封的解析/接受结果

| 信封 | 次数 | 解析成功 | SQLite 接受 |
|---|---:|---:|---:|
| `alias_pair:function+arguments` | 592 | 592/592 (100.00%) | 571/592 (96.45%) |
| `canonical_function+params` | 397 | 397/397 (100.00%) | 370/397 (93.20%) |
| `invalid_envelope` | 103 | 0/103 (0.00%) | 0/103 (0.00%) |
| `alias_pair:function+parameters` | 11 | 11/11 (100.00%) | 11/11 (100.00%) |
| `alias_pair:function+function_args` | 5 | 5/5 (100.00%) | 5/5 (100.00%) |
| `invalid_json` | 2 | 0/2 (0.00%) | 0/2 (0.00%) |
| `invalid_single_key_call` | 1 | 0/1 (0.00%) | 0/1 (0.00%) |


### 非法 envelope 的原始 key 形状

先按结构族聚合：

| 结构族 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `operation_arguments_with_metadata` | 42 | 103 | 40.78% | 31.78%–50.43% |
| `function_arguments_with_extra_fields` | 23 | 103 | 22.33% | 15.37%–31.28% |
| `operation_result_record_echo` | 21 | 103 | 20.39% | 13.74%–29.17% |
| `nested_function_object` | 8 | 103 | 7.77% | 3.99%–14.58% |
| `other_invalid_envelope` | 5 | 103 | 4.85% | 2.09%–10.86% |
| `ambiguous_or_extra_registered_call_fields` | 3 | 103 | 2.91% | 1.00%–8.22% |
| `unregistered_operation+arguments_pair` | 1 | 103 | 0.97% | 0.17%–5.30% |

再列精确 key 组合：

| key 形状 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `arguments+function+id` | 19 | 103 | 18.45% | 12.14%–27.02% |
| `arguments+id+operation` | 18 | 103 | 17.48% | 11.35%–25.94% |
| `arguments+id+operation+type` | 13 | 103 | 12.62% | 7.53%–20.40% |
| `arguments+operation+output+success` | 12 | 103 | 11.65% | 6.79%–19.27% |
| `function<object:arguments+name>` | 8 | 103 | 7.77% | 3.99%–14.58% |
| `arguments+error+operation+output+success` | 6 | 103 | 5.83% | 2.70%–12.13% |
| `arguments+operation+path` | 4 | 103 | 3.88% | 1.52%–9.56% |
| `arguments+function+id+type` | 3 | 103 | 2.91% | 1.00%–8.22% |
| `arguments+description+id+type` | 2 | 103 | 1.94% | 0.53%–6.81% |
| `arguments+id+operation+version` | 2 | 103 | 1.94% | 0.53%–6.81% |
| `function+type` | 2 | 103 | 1.94% | 0.53%–6.81% |
| `arguments+check_command+operation` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+description+function` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+description+path+type` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+id+operation+status` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+name+type` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+output+status` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+output_format+request_id+timestamp+tool_name` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+request_id+timestamp` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+request_id+type` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+request_id+version` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `arguments+operation+run_id+status` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `function+function_name+params` | 1 | 103 | 0.97% | 0.17%–5.30% |
| `function+name+params` | 1 | 103 | 0.97% | 0.17%–5.30% |

## Model-I/O 转换序列

| 转换序列 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `call_envelope:function+arguments->function+params` | 592 | 1111 | 53.29% | 50.35%–56.20% |
| `<none>` | 503 | 1111 | 45.27% | 42.37%–48.21% |
| `call_envelope:function+parameters->function+params` | 11 | 1111 | 0.99% | 0.55%–1.76% |
| `call_envelope:function+function_args->function+params` | 5 | 1111 | 0.45% | 0.19%–1.05% |

## 解析出的 operation

| operation | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `final_answer` | 437 | 1111 | 39.33% | 36.50%–42.24% |
| `read_file` | 190 | 1111 | 17.10% | 15.00%–19.43% |
| `read_json` | 128 | 1111 | 11.52% | 9.77%–13.53% |
| `<unparsed>` | 106 | 1111 | 9.54% | 7.95%–11.41% |
| `check_command` | 54 | 1111 | 4.86% | 3.74%–6.29% |
| `write_json` | 48 | 1111 | 4.32% | 3.27%–5.68% |
| `file_digest` | 39 | 1111 | 3.51% | 2.58%–4.76% |
| `write_file` | 38 | 1111 | 3.42% | 2.50%–4.66% |
| `replace_text` | 34 | 1111 | 3.06% | 2.20%–4.25% |
| `patch_json` | 14 | 1111 | 1.26% | 0.75%–2.10% |
| `run_command` | 10 | 1111 | 0.90% | 0.49%–1.65% |
| `remove_line` | 5 | 1111 | 0.45% | 0.19%–1.05% |
| `list_directory` | 3 | 1111 | 0.27% | 0.09%–0.79% |
| `bind_evidence` | 2 | 1111 | 0.18% | 0.05%–0.65% |
| `copy_file` | 2 | 1111 | 0.18% | 0.05%–0.65% |
| `make_directory` | 1 | 1111 | 0.09% | 0.02%–0.51% |

## 解析失败

| 失败类 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `missing_or_ambiguous_envelope_keys` | 78 | 106 | 73.58% | 64.47%–81.05% |
| `extra_envelope_fields` | 25 | 106 | 23.58% | 16.52%–32.50% |
| `invalid_json` | 2 | 106 | 1.89% | 0.52%–6.62% |
| `invalid_single_key_call` | 1 | 106 | 0.94% | 0.17%–5.15% |

## 全部协议/schema 拒绝

| 拒绝类 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `missing_or_ambiguous_envelope_keys` | 78 | 154 | 50.65% | 42.83%–58.43% |
| `path_or_string_constraint` | 29 | 154 | 18.83% | 13.44%–25.74% |
| `extra_envelope_fields` | 25 | 154 | 16.23% | 11.24%–22.87% |
| `operation_not_displayed` | 8 | 154 | 5.19% | 2.66%–9.92% |
| `unknown_arguments` | 8 | 154 | 5.19% | 2.66%–9.92% |
| `argument_type` | 2 | 154 | 1.30% | 0.36%–4.61% |
| `invalid_json` | 2 | 154 | 1.30% | 0.36%–4.61% |
| `invalid_single_key_call` | 1 | 154 | 0.65% | 0.11%–3.59% |
| `missing_required_arguments` | 1 | 154 | 0.65% | 0.11%–3.59% |

注意：这里的 parser failure 是 JSON/call-envelope 格式失败；其余拒绝发生在 operation 可见性或 ActionDefinition 参数 schema 层。两者不能合并成“格式转换失败”。

## Accepted action 参数转换序列

| 转换序列 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `<none>` | 231 | 520 | 44.42% | 40.21%–48.72% |
| `registry_default:max_tokens | registry_default:start_byte` | 122 | 520 | 23.46% | 20.02%–27.29% |
| `registry_default:create_parents | registry_default:overwrite` | 41 | 520 | 7.88% | 5.87%–10.52% |
| `registry_default:start_byte` | 41 | 520 | 7.88% | 5.87%–10.52% |
| `registry_default:max_tokens` | 40 | 520 | 7.69% | 5.70%–10.31% |
| `registry_default:env` | 25 | 520 | 4.81% | 3.28%–7.00% |
| `registry_default:env | registry_default:expected_exit_code | registry_default:timeout` | 6 | 520 | 1.15% | 0.53%–2.49% |
| `registry_default:all` | 3 | 520 | 0.58% | 0.20%–1.68% |
| `registry_default:create_parents` | 3 | 520 | 0.58% | 0.20%–1.68% |
| `registry_default:env | registry_default:timeout` | 3 | 520 | 0.58% | 0.20%–1.68% |
| `explicit_unit:timeout_ms->timeout_seconds` | 1 | 520 | 0.19% | 0.03%–1.08% |
| `explicit_unit:timeout_ms->timeout_seconds | registry_default:env` | 1 | 520 | 0.19% | 0.03%–1.08% |
| `registry_default:overwrite` | 1 | 520 | 0.19% | 0.03%–1.08% |
| `registry_default:parents` | 1 | 520 | 0.19% | 0.03%–1.08% |
| `registry_default:recursive | registry_default:start_after` | 1 | 520 | 0.19% | 0.03%–1.08% |

`registry_default:*` 只补 ActionDefinition 已公开的固定默认值；alias/unit/null/annotation 等转换只搬运或删除已显式给出的非语义接口信息。转换层不补 operation、path、content、value 或答案。

## 按难度层级

| 层级 | 请求 | 解析成功 | SQLite 接受 | model-I/O 有转换 |
|---|---:|---:|---:|---:|
| B | 478 | 454/478 (94.98%) | 441/478 (92.26%) | 311/478 (65.06%) |
| M | 424 | 365/424 (86.08%) | 353/424 (83.25%) | 192/424 (45.28%) |
| H | 186 | 165/186 (88.71%) | 142/186 (76.34%) | 92/186 (49.46%) |
| LH | 23 | 21/23 (91.30%) | 21/23 (91.30%) | 13/23 (56.52%) |


活跃 case 口径（分母 53，同一 case 可命中多个类别）：

| case 事件 | 次数 | 分母 | 概率 | Wilson 95% CI |
|---|---:|---:|---:|---:|
| `at_least_one_canonical_envelope` | 53 | 53 | 100.00% | 93.24%–100.00% |
| `at_least_one_model_io_conversion` | 53 | 53 | 100.00% | 93.24%–100.00% |
| `at_least_one_rejection` | 36 | 53 | 67.92% | 54.52%–78.91% |
| `at_least_one_parser_failure` | 35 | 53 | 66.04% | 52.59%–77.31% |

## 数据库核对

- 扫描 500 个 SQLite v3 store；`PRAGMA quick_check` 全部为 `ok`：True。
- append-only decision events：1111；唯一 request_id：1111。
- 数据库保存完整 `DecisionRecord.raw_output`，而不仅是 digest；accepted action 事件还保存 `argument_normalization`。
- Trace 是每次模型 session 的独立生成审计；SQLite 是运行状态/因果事件权威源。两者本轮可以按 request_id 无损合并，因为覆盖和 raw bytes 一致性已经通过。

## 转换层静态接受集合

当前 call-envelope 层接受：

1. name key：`function` / `name` / `tool`；
2. argument key：`params` / `parameters` / `arguments` / `args` / `function_args`；
3. 上述一对 key 的 15 种组合（对象不得有第三个字段），或 `{"<operation>": {...}}` 单键调用；
4. bare JSON、完整 `json` Markdown fence、完整无语言 Markdown fence；可去首尾空白；
5. 统一投影为 wire `{"function": name, "params": arguments}`，内部 `ModelCommand(name, arguments)`。

它明确拒绝多个候选、额外 envelope 字段、缺 name/arguments、非对象 params、非 JSON、未闭合/非 JSON fence。参数层只执行 `action-arguments.v2` 中登记的透明转换，之后仍由精确 ActionDefinition schema fail-closed。

参数层静态登记的输入变体为：`write_json.content→value`（若 content 是字符串先按 JSON 解析）、
`replace_text.text→new`、`replace_text.count="all"→all=true`、
`run_command/check_command.timeout_ms→timeout` 秒、`shell=false` 删除、`env=[]→{}`；
另删除不属于工具 schema 的观测注释字段、把 optional null 当作省略，并填充 registry 中公开的固定默认值。
冲突 alias、无法解析的 JSON string、`shell=true`、未知字段和 schema 不匹配继续拒绝。

## 适用范围限制

Round162 使用 `tool_disclosure=full`。当前工作树默认的 progressive 两阶段 `select_tool → disclosed operation` 尚无同规模正式数据；本报告不得当作 progressive 模式下 select-tool 格式概率。概率也是该固定任务/模型/采样/Prompt 下的经验频率，不是模型在任意 Prompt 下的先验概率。

同一 case 内的 retry/correction 输出相关，1,111 次返回只有 903 个唯一 raw SHA-256；Wilson 区间仅作为逐响应经验比例的描述区间，不宣称样本完全独立。

## 复核材料

- `statistics.json`：全部计数、分母、概率和 Wilson 区间。
- `raw_examples.json`：按格式/失败类确定性选取的完整原始输出及 request/source 引用。
- `source_manifest.json`：90 个 trace、全部数据库和解释代码的大小/SHA-256/用途。
- 生成脚本：`temp/analyze_round162_rwkv_format_distribution.py`。
