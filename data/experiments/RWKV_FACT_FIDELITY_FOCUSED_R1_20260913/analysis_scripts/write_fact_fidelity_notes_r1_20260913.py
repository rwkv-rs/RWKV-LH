from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913');notes={}
def add(name,requirements,findings):
 a=json.loads((D/'runs'/name/'execution/RESULT.json').read_text())['final']
 assert all(f['quote'] in a for f in findings)
 notes[name]=dict(answer_sha256=hashlib.sha256(a.encode()).hexdigest(),requirements=requirements,findings=findings)
add('rag_overview-focused-r1',[('numbers','met','候选标签与17/36、zero10/36及Reader48/60到60/60均正确；等价百分比换算不当作篡改数字'),('limits','partial','泛化限制正确，但加入无依据的各自前后提升关系')],[dict(kind='contradiction',severity='minor',quote='从约 47.2% 提升到约 47.2%',reason='原文报告两种State的横向成绩，没有这种相同数值的前后提升；同样错误出现在zero27.8%表述',impact='比较关系表述不正确；原始成绩及候选归属仍正确，因此保留部分满足，不与改写原分数等同')])
add('rag_overview-focused-r2',[('numbers','met','候选标签、分数对象与分子分母忠实引用，无新增成绩'),('limits','met','受控范围、扩大1400条不继续提升和能力上限限制均正确')],[])
add('api_bug-focused-r1',[('bug','unmet','虽指出冲突检测缺失，但编造已有POST解析/SQLite写入，未按实际骨架解释缺陷'),('provenance','partial','建议明确为尚未执行，没有虚称实测；遗漏本次实际工具操作，并混淆需求和源码事实'),('verification','partial','给出具体重叠请求验证思路，但建立在不存在的实现上')],[dict(kind='unsupported',severity='material',quote='它接收 start/end 后直接写入数据库',reason='实际server.py仅实现GET /health与其他GET501，无POST解析或SQLite写入',impact='核心缺陷触发及后果建立在虚构代码上，不能据此修改冲突检测')])
add('api_bug-focused-r2',[('bug','partial','数据库与业务功能缺失有事实基础，但混入启动报错、连接泄漏和未实现健康检查等错误'),('provenance','partial','正确标记验证尚未执行，未报告本次读取工具；源码、需求与推断混淆'),('verification','partial','列出建议测试类别，但缺少针对真实缺陷的具体预期且含不存在连接的关闭测试')],[dict(kind='contradiction',severity='material',quote='代码中没有实现，只是返回了 404',reason='实际GET /health实现返回200和ok:true；其他GET返回501',impact='将已有正常实现误报为缺失，并虚构状态码'),dict(kind='unsupported',severity='material',quote='因此第一次启动时会报错',reason='代码不使用数据库参数，缺失连接并不触发启动报错；已有外部实际启动验证通过',impact='误导用户定位不存在的启动故障'),dict(kind='contradiction',severity='material',quote='README 中没有说明如何检测同 resource 的时间重叠',reason='README明确给出重叠条件与409冲突要求',impact='把已写明的需求当作缺失')])
(D/'MANUAL_REVIEW_NOTES.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
