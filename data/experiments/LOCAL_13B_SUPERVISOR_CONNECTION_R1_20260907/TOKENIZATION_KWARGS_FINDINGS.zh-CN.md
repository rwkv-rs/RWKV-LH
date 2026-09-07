# 本地 13.3B chat-template 参数传递核对

结论：本次实际 tokenization 路径中，`rwkv_generation_prompt='fake_think'` **未改变渲染后的模型输入**。它与 `open_think` 的全部 token ID、完整解码文本及 token 数完全相同，末尾仍为 `\nBot✿<think`，没有 fake 模式预期的 `</think` 部分。因此，既有 `WIRE_FAKE_THINK.json` 不能作为“fake 前缀已生效但模型仍坚持推理”的证据。

本次只使用同一个已经记录的完整 Planner body 的模型名、messages 和模板相关字段，保留消息内容。未发送任何 generation 请求，未修改模型、服务、配置、生产代码、角色协议或 State，也未执行远端 Git。

## 实测

服务 `/v1/models` 恢复并包含目标模型后才开始请求。模型为 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，地址为本地转发 `http://127.0.0.1:29613`。

| 请求差异 | tokenize / detokenize | token 数 | 解码尾缀 |
| --- | --- | ---: | --- |
| `rwkv_generation_prompt=open_think` | 200 / 200 | 1,984 | `\nBot✿<think` |
| `rwkv_generation_prompt=fake_think` | 200 / 200 | 1,984 | `\nBot✿<think` |
| 自定义 mode 为非法诊断值 | 200 / 200 | 1,984 | `\nBot✿<think` |
| `add_generation_prompt=False` | 200 / 200 | 1,979 | 用户消息后的 `✿`，没有 Bot/think 前缀 |

前三组 token ID SHA-256 均为 `034d5c754a7bb492de205a206a841fefca18f8199d1c32ee082ad3a162aca39c`，完整解码文本 SHA-256 均为 `cd09dcc6e9eadccbb4bf5f66236291566a9291a90d2c055cae0c16faa2ef3cda`。关闭 generation prompt 的控制请求产生不同文本和 token 序列，证明接口确实处理了已接受的模板参数。

请求总数为 GET `/v1/models` 1 次、POST `/tokenize` 4 次、POST `/detokenize` 4 次；generation 为 0。接口 schema 已先从当前远端 engine 源码核实，没有通过猜测字段或生成请求探测。

## 源码解释与证据范围

当前 engine 位于 `/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50`。只读核对得到：

1. `vllm/entrypoints/serve/tokenize/protocol.py` 的 `TokenizeChatRequest` 明确接受 `chat_template_kwargs`，并将它与 `add_generation_prompt` 等参数合并为 `ChatParams`；tokenize 的输出预算是 0。
2. `vllm/entrypoints/serve/tokenize/serving.py` 使用 `online_renderer.preprocess_chat` 渲染，不调用生成。
3. `vllm/renderers/hf.py:633` 的 `resolve_chat_template_kwargs` 只保留 tokenizer 显式签名参数、Jinja 模板变量和 HF 标准参数；其签名检查指定 `allow_var_kwargs=False`。`safe_apply_chat_template` 在调用 tokenizer 前经过这个筛选。
4. `vllm/tokenizers/rwkv.py:369` 的 `apply_chat_template` 把 `rwkv_generation_prompt` 放在 `**kwargs` 中读取，未在函数签名中显式声明。
5. `vllm/tokenizers/rwkv_defaults.py` 的 native 模板是纯注释 `{# RWKV native chat template #}`，没有声明自定义 Jinja 变量；默认模式为 `open_think`。直接的 native 渲染器本来只接受 open/fake 两种值：open 应返回 `<think`，fake 应返回 `<think></think`，末尾均没有 `>`。

源码链与实测一致：该自定义参数不属于筛选接受集合，因此可能在 tokenizer 的 native 渲染逻辑读取前被丢弃，随后落回 `open_think`。非法 mode 也未触发 native mode 校验，而标准 generation-prompt 控制参数有效，进一步支持这一定位。

此结论严格针对已观察的参数传递和渲染结果。本次没有重新做生成，不能判断修正参数传递后模型能否按要求产生可解析 Planner JSON。此前完整 fake 请求记录的 prompt token 数也是 1,984，但计数一致本身不代替逐 token 的生成输入证据。

该发现与 `response_format=json_object` 的 HTTP 500 是不同问题；本报告不将 kwargs 筛选认定为 HTTP 500 根因，也不混入 benchmark 或训练结果。

## 工件与 SHA-256

- `TOKENIZATION_KWARGS_RENDER_COMPARISON.json`：完整 tokenization 请求、返回 token ID、detokenize 结果、控制组和已读 engine 文件 SHA。SHA-256：`63181b05a9727676925c75e1ead08aa0a8f1ef577a008d3976266d5506baf5f8`。
- `temp/probe_local_13b_tokenization_kwargs_20260907.py`：本地执行脚本；只允许上述三个 endpoint。脚本 SHA 已记录在 JSON 工件内。
- 原始消息来源为本轮 `WIRE_FAKE_THINK.json` 的 `request_body`；来源 SHA 已记录在 JSON 工件内。没有手工重造角色协议输入。
