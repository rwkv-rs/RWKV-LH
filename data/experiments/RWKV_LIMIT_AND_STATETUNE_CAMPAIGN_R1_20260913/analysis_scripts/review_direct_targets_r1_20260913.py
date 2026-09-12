from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/curation'
notes={
'file-01':(True,'覆盖备份/还原目的、清单格式、安全校验与失败保留；明确为实现要求，未声称已测试。内容较长但忠实。'),
'file-02':(False,'生成在4096输出预算中断，没有完整候选；保留失败，不补写标签。'),
'file-03':(True,'工单目标、创建/分配/关闭/搜索和持久化/公开UI约定均有来源；是需求概要，不是实施证明。'),
'file-04':(True,'投票、幂等、服务端关闭限制、API/UI和持久化均源自README；未加认证事实。'),
'file-05':(True,'明确这是待修复的迁移项目，备份、原子发布/恢复、类型保真和命令约定准确。'),
'file-06':(False,'虽先提及写备份，但随后把version=2返回概括为不做改动，可能掩盖此前无条件覆写备份这一真实副作用；不收作可信训练标签，不自动改写。'),
'file-07':(True,'四函数的完整性/列存在检查、只读源backup、fsync和硬链接发布/清理准确；无顶层逻辑按无业务调用理解，非否认import执行。'),
'file-08':(True,'已有缺陷与待满足约定明确，内容同步/删除/Unicode/原子失败/重启要求准确，未转成实现证明。'),
'file-09':(True,'基于glob、lower、replace解码以及摘要/mtime记录说明现有行为，不虚构递归扫描或NFC功能。'),
'file-10':(True,'连接、mtime判断、逐行提交、generation每调用递增和状态查询准确；指出没有删除操作。只统计理解为整体计数，未声称deleted会增加。')}
rows=[]
for name,(accepted,note) in notes.items():
 result=json.loads((D/name/'RESULT.json').read_text());boundary=json.loads((D/name/'SOURCE_BOUNDARY.json').read_text());assert result['input_sha256']==hashlib.sha256(boundary['input_text'].encode()).hexdigest()
 review={'reviewer':'Codex independent visible-source review 2026-09-13','accepted':accepted,'target_sha256':result['target_sha256'],'input_sha256':result['input_sha256'],'visible_evidence_only':True,'note':note}
 path=D/name/'CODEX_REVIEW.json';assert not path.exists();path.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');rows.append({'id':name,**review})
(D/'CODEX_REVIEWS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
