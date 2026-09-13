from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
notes={}
def put(name,requirements,findings=()):
    answer=json.loads((D/'runs'/name/'execution/RESULT.json').read_text())['final']
    notes[name]={'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),'requirements':requirements,'findings':list(findings)}
def wrong_numeric(quote):return {'kind':'contradiction','severity':'material','quote':quote,'reason':'原文Writer300是候选标签，固定组为17/36，对照zero10/36；回答报告了文件不支持的实验分数','impact':'改变用户询问的实验结果及改善幅度，不能作为正确实验概览'}
put('rag_overview-serial-r1',[('stack','partial','模型与无embedding正确，但遗漏明确询问的BM25检索方式'),('limits','partial','受控实验与泛化限制基本正确，Writer数字有实质错误')],[wrong_numeric('Writer 在固定 36 题中从 17/36 提高到 30/36')])
put('rag_overview-parallel-r1',[('stack','met','RWKV2.9B、BM25与无embedding均正确'),('limits','partial','边界说明正确但Writer实验分数错误')],[wrong_numeric('Writer 在固定 36 题中从 17/36 提高到 30/36')])
put('rag_overview-parallel-r2',[('stack','met','模型、BM25与无embedding均正确'),('limits','partial','正确保留泛化与默认State限制，但实验数字编造')],[wrong_numeric('Writer 从 17/36 提高到 300/1000')])
for name in ['rag_rules-serial-r1','rag_rules-parallel-r1']:
    put(name,[('material','met','准确说明选中的逐字证据与切片原子性/overlap'),('roles','met','模型语义决定和程序检索传输解析校验职责正确'),('audit','met','保留原始输出、精确prompt与证据ID，不由程序补写答案')])
put('rag_rules-parallel-r2',[('material','partial','说明Writer只看选中的逐字证据；遗漏冻结要点内的切片overlap/结构。该细节是否应为必要项存在契约粒度问题，原口径保留partial，不能称为无法回答主问题'),('roles','met','模型与程序职责正确'),('audit','met','原始回答与调用来源记录约束正确')])
put('backup_check-parallel-r2',[('behavior','partial','不会覆盖的结论正确，但机制及返回行为均编造'),('proof','unmet','不存在create_backup或os.path.exists检查；验证方法依赖不存在函数和False返回')],[{'kind':'unsupported','severity':'material','quote':'在 create_backup 函数中，使用 os.path.exists 检查目标文件是否存在，如果存在则直接返回','reason':'实际函数write_backup_exclusive调用os.link排他创建，目标存在时抛FileExistsError，finally清理暂存文件','impact':'编造代码依据和验证方法，不能作为有效代码检查报告'}])
(D/'MANUAL_REVIEW_NOTES_PARTIAL.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
