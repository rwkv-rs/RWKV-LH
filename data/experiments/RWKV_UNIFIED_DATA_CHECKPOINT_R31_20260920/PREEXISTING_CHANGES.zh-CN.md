# 接手时已有的五处修改说明

“五处修改”是本轮接手工作区时已经存在的未提交差异；这不是作者身份判断，不能由此称为 owner 亲自编写的修改。本轮未覆盖、回退或重写这五个文件。

- `rwkv_lh/controller.py`：强模型在线协助的每个已提交微任务绑定一次新 Actor State；限定本轮待注入观察，恢复时避免重复初始化。
- `rwkv_lh/model.py`：实现微任务 Actor State 初始化，带入明确选择的真实执行事实，登记旧 checkpoint 与未继承 Actor State 的关系，并拒绝未决选择等不合法边界。
- `rwkv_lh/supervisor_openai.py`：校验强模型响应顶层结构；不合规响应留痕并在预算内重新请求模型，配套明确计划、审核与指令提示。
- `tests/test_hybrid_supervisor.py`：微任务 State、事实隔离及恢复幂等测试。
- `tests/test_supervisor_openai.py`：强模型不合规响应拒绝与重试测试。

本地差异合计619行新增、79行删除。该内容涉及强模型协助路径，与R28训练目标外层 function/params 格式修复不是同一改动。数据扩充期间只保留这些差异，不将其混入本轮数据提交。它们已经包含在当前源码冻结清单与1910项完整工程回归中；保留不等于跳过验证，也不能由单元回归推导线上任务验收通过。

逐文件SHA如下（与上述完整回归的源码身份再次比较一致）：

- `rwkv_lh/controller.py`：`02020ad7df9d94192ebbf449383c328b8ab1f24129714a56be172c77feb42dc9`
- `rwkv_lh/model.py`：`fe69d631a1957d6894ecaa2cd6b6051145d4ebbb9c2bd61184574d99e381dae6`
- `rwkv_lh/supervisor_openai.py`：`1ed4b58917f17266d95cedcdc1a4c893e7944f8b782c398357d3f19740d7cb10`
- `tests/test_hybrid_supervisor.py`：`0cd03caa0c56c084cc018f0f2930cf6de07338b3bcd14b74e0addcff197684b8`
- `tests/test_supervisor_openai.py`：`32c61aeeb3dcb07a616c24bba20e5c72eafbe65ef36f6d278502a56b444caeb5`
