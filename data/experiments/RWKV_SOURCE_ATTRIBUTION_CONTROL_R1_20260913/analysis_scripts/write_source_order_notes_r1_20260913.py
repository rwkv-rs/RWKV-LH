from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913/order_probe');notes={}
for rep in (1,2):
 name=f'code_and_requirements-focused-r{rep}';a=json.loads((D/'runs'/name/'execution/RESULT.json').read_text())['final']
 req=[('http','partial','健康接口和业务未实现正确，但其他GET应为501，回答混入或确定报告404'),('db','met','准确说明必填解析、未使用与无数据库实现'),('sources','met' if rep==1 else 'partial','如实报告读取与未运行，建议验证合理' if rep==1 else '如实报告读取但没有具体建议验证，额外把已有JSON响应泛称为未实现')]
 findings=[dict(kind='contradiction',severity='minor' if rep==1 else 'material',quote='404 或 501' if rep==1 else '其他路由返回 404',reason='实际其他GET固定501和not_implemented；404来自需求约定，不是当前源码行为',impact='保留业务未实现和db未使用的正确判断；状态码回答仍不准确' if rep==1 else '用户明确询问实际HTTP行为，确定报告404会误导行为验证')]
 if rep==2:findings.append(dict(kind='contradiction',severity='minor',quote='JSON 响应、路由规则等均未在 server.py 中实现',reason='健康接口及其他GET已有JSON响应；不能将业务未实现扩展成所有JSON响应未实现',impact='末尾泛化与前文已有健康JSON自相矛盾'))
 assert all(f['quote'] in a for f in findings)
 notes[name]=dict(answer_sha256=hashlib.sha256(a.encode()).hexdigest(),requirements=req,findings=findings)
(D/'MANUAL_REVIEW_NOTES.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
