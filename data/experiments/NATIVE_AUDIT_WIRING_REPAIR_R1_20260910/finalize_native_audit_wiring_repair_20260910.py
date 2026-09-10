"""Record the bounded engineering step without claiming a new Agent score."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/NATIVE_AUDIT_WIRING_REPAIR_R1_20260910'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
log = (OUT / 'PYTEST.log').read_text()
match = re.search(r'(\d+) passed in ([\d.]+)s', log)
if not match or ' failed' in log or ' skipped' in log:
    raise SystemExit('Complete green pytest required')
passed, seconds = int(match[1]), float(match[2])
paths = ['rwkv_lh/model_session.py', 'rwkv_lh/runtime/openai_compat.py', 'tests/test_native_request_recovery.py']
patch = subprocess.check_output(['git', 'diff', '--', *paths], cwd=ROOT)
(OUT / 'CHANGE.patch').write_bytes(patch)
for name in ('check_selector_admission_after_audit_repair_20260910.py', 'finalize_native_audit_wiring_repair_20260910.py'):
    shutil.copyfile(ROOT / 'temp' / name, OUT / name)
status = {
    'agent_latest': {'source': 'R2 linked same-source 15-task coverage view', 'strict': 0,
                     'completed': 0, 'selected': 15, 'mutations': 6,
                     'terminations': {'no_progress': 10, 'executor_protocol': 4, 'step_auditor_protocol': 1}},
    'capability': 'Can write source files in a prepared workspace; independent full project delivery is not demonstrated.',
    'current_repair_agent_evaluation': 'not_run', 'old_runs_valid_as_current_candidate_comparison': False,
    'engineering': {'initial_red': 3, 'targeted_passed_before_four_role_test': 150,
                    'recovery_suite_passed': 67, 'full_passed': passed, 'failed': 0, 'skipped': 0,
                    'full_seconds': seconds},
    'source_sha256': {path: sha(ROOT / path) for path in paths},
    'optimizer_steps': 0, 'formal_dataset_created': False, 'server_changed': False,
    'next_data_gates': ['exact source compatibility review for new SHAs', 'execute coverage',
                        'fixed split similarity', 'independent semantic labels'],
}
(OUT / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
report = f'''# Native 审计接线修复与项目能力状态

最新 Agent 证据仍为十五题关联视图 Strict 0/15、completed 0/15、mutation 6；10题无进展、4题Executor协议拒绝、1题Step Auditor协议拒绝。该数据来自修复前冻结版本，本轮没有新 Agent 成绩，旧结果用于新源码候选对比时 INVALID，原始结果保持不变。

**当前能在已提供的工作区创建代码文件并开始修改，尚不能认定会自主创建并完成一个可验收的项目。** 三道 Ultra 题和 WEB-02 已有真实写入；测试工作区由 runner 预备，不能把它写成 Agent 已独立完成项目初始化。完整回归验证工程行为，不等价于需求完成、运行调试和交付验收。

本次已执行的下一步是修复 Native 首错审计的统一接线。`create_model_session` 在 capability 检查前订阅会话回调，`ModelSession` 构造也覆盖直接创建路径；客户端保存原有回调并去重订阅，逐回调捕获异常，避免一个失败观察者阻断其他观察者和请求恢复。四角色仍各用独立客户端，不引入角色状态共享、额外模型调用或工具特判。

三个新测试在原代码全部失败：工厂隐式/显式客户端的首错都未送达，以及已有失败回调导致会话收不到事件。修复后三项通过；新增真实 benchmark 四角色工厂恢复测试，逐角色执行连接错误、404、404、成功重发，验证每角色恰好三个事件、首因文本完整、角色标签不串线。已有 Native 未知结果不可重发、重发上限、去重和生命周期测试继续通过。专项先150通过，包含新四角色用例的恢复套件67通过；完整 **{passed} passed、0 failed、0 skipped，{seconds:.2f}秒**。

工程接线缺陷已修复并通过本地回归，但不能据此宣布 Agent KEEP 或整体项目已完成验收。模型、协议、预算、评分和服务部署未变；本轮未跑新模型评测。此变更增加底层审计事件，日志体积会增长；以后用新冻结源码登记对比双方，不能重评分旧trace宣称提升。

Selector 下一步准入检查也已执行，见 `SELECTOR_ADMISSION_PREFLIGHT.json`：十五个旧来源均因 model_session.py SHA 变化被现有准入器拒绝。历史双AI waiver只授权原14来源/Selector及其精确SHA，不能自动扩大到新源码，原九边界/27行和旧审批都保留。原候选还有 execute=0、101/281跨切分对超阈值、语义标签未批准三项质量门。未启动训练、未建立新 data/datasets 版本；低Agent分数本身不构成训练禁令，实际障碍是当前角色数据与来源门。

状态推进顺序：新源码等价复核/冻结来源 → 补足合法生产trace中的Selector覆盖并消除固定切分泄漏 → 独立语义标签复核 → 登记已授权首轮Selector StateTune及固定回归比较。前序State合格后再推进Executor等角色。三项流程优化仍排首轮StateTune后独立立轮；本次不扩大成架构重写。

源码/测试SHA在STATUS.json，修复diff在CHANGE.patch，先失败后通过及完整测试原日志、准入检查和脚本全部按EVIDENCE_SHA256.json登记。旧R1/R2未改分、未修改，Holdout未读取，服务器未执行Git，owner负责push。
'''
(OUT / 'REPORT.zh-CN.md').write_text(report)
files = [{'path': str(path.relative_to(OUT)), 'sha256': sha(path), 'bytes': path.stat().st_size}
         for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'EVIDENCE_SHA256.json']
(OUT / 'EVIDENCE_SHA256.json').write_text(json.dumps({'files': files}, indent=2) + '\n')
print(json.dumps({'passed': passed, 'seconds': seconds, 'report_sha256': sha(OUT / 'REPORT.zh-CN.md'),
                  'evidence_sha256': sha(OUT / 'EVIDENCE_SHA256.json')}))
