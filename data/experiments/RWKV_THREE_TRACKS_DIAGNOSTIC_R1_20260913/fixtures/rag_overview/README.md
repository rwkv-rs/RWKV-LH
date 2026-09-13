# RWKVRAG — RWKV 原生 RAG

基于 `bm250820` 的 `2bbc406125e7e030eda98b11993dc13fc4534ca4` 开发，当前优化分支为 `chase/rwkv-native-rag-rebuild`。

**RWKV 2.9B + OpenSearch BM25，不使用 embedding。** 模型负责问题规划、证据判断与回答；代码负责检索组织、传输、来源与格式校验。原始模型输出保持不变。

## StateTune 实践

[StateTune经验总结](docs/statetune-experience.md)记录本轮如何从真实trace发现问题、生成2000条纠错数据、完成六组state训练，以及改善与失败。

Reader在60道受控阅读挑战中从48/60提高到60/60。Writer明显减少失控重复；固定36题的独立抽样中，Writer300有据可用17/36，零state为10/36，扩大到1400条没有继续提高。Planner出现格式退步，空证据和冲突处理仍不可靠。这些结果不是全场景准确率，也不代表模型能力上限。

- [数据与训练入口](llamaindex-retrieval/statetune/README.md)
- [原始实验记录、权重和恢复方式](docs/artifacts.md)
- [最新训练核验](llamaindex-retrieval/eval/trace-training-20260911/TRAINING-VERIFIED.json)
- [最新评测汇总](llamaindex-retrieval/eval/trace-eval-20260911/RESULTS.md)

## 使用

通用安装与接口见[Python服务说明](llamaindex-retrieval/README.md)，现有环境的管理方式见[本地部署说明](llamaindex-retrieval/deploy/local/README.md)。本地页面为 <http://127.0.0.1:18440/admin/#/search>，通过后端 `POST /v1/ask` 执行真实RAG；API接口文档为 `/docs`。现有前端已恢复用于人工试用。

仅使用指定的RWKV7 G1j 2.9B。训练后的state必须显式选择；训练完成不等于应用默认配置已经切换。2026-09-11测试结束后，按用户要求保留比较服务，没有恢复原问答服务。

现有页面已接入此前评测使用的 **5000篇FineWiki中文文章、45960个原文片段**。选择“FineWiki 中文百科（5000篇）”即可试用，文件列表支持完整分页。[试用指南、13道测试题与参考答案](docs/wiki-rag-test-guide.md)包含原文依据、接入方法和实际试用记录，适合转发学习。

复杂多问、长历史、缺证据与引用仍有已知错误。服务可访问不代表所有场景已可靠。架构约束见[ARCHITECTURE_RULES.md](llamaindex-retrieval/ARCHITECTURE_RULES.md)。

## 开发验证

```bash
cd llamaindex-retrieval
uv sync --frozen --extra dev
uv run pytest -q
```

历史实验的独立重放需要先按[归档说明](docs/artifacts.md)恢复相应文件；普通代码测试所需的小型固定材料保留在Git中。发布时的实际检查结果见 `artifacts/statetune-20260911/VALIDATION.json`。

仓库保留维护中的代码、训练入口、正式数据和必要测试材料；原始调用、冻结源码与过时实验说明统一归档。旧Git提交保持不变。
