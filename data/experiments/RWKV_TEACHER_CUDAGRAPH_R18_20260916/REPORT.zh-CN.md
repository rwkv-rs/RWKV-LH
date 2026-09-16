# R18：开启 CUDA Graph 并恢复教师纠错

任务级：首两题 R17 均 output_budget_exhausted、0产物通过，原结果保留。切换时另两题中断并单独封存 outputs/interrupted_r18，显式回到 pending 重试；不算合格，不覆盖原轨迹。1024来源不变。未训练。

仅移除 --enforce-eager，vLLM 默认同时启用编译与 CUDA Graph，因此收益归于该部署配置整体，不单独归因 Graph 内核。模型BF16、GPU0+3 TP2、262144上下文、并发2、采样和任务预算不变。官方引擎/模型逐文件清单仍启动核验；新启动脚本本地 SHA 与远端核对。未远端 Git。

同两份生产第二次调用输入，seed18，每请求256token、ignore_eos，三轮双并发，第一轮预热；短输出探针不算任务通过。Eager预热后27.2213 token/s，Graph 82.6547 token/s，3.0364倍；各响应输入/输出token IDs与usage一致。全部原始响应见 EAGER_R18.json、GRAPH_R18.json。编译约4分钟，日志确认 Graph capturing finished。该短探针不能保证长生成同等加速，更不能证明代码正确率改善。

模型unit为 rwkv-lh-teacher-graph-r18.service，API仍18244/原模型别名。队列unit仍 rwkv-lh-teacher-1024-r17.service，运行目录不变；outputs/ENGINE_TRANSITION_R18.json显式绑定新引擎身份。首次尝试start旧瞬态unit因stop后unit已卸载失败，随后用原命令重新创建，未丢失SQLite队列。

仍存在长思考耗尽输出的问题，本轮未改reasoning预算以隔离速度比较。下一步用固定任务验证思考预算，不能把吞吐收益当纠正质量收益。源码业务逻辑未修改，owner五处修改保留，未push。

完整仓库回归：1894 passed、0 skipped，336.33秒，见 FULL_TESTS.txt。
