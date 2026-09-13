from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913');notes={}
def add(name,requirements,findings):
 a=json.loads((D/'runs'/name/'execution/RESULT.json').read_text())['final'];assert all(f['quote'] in a for f in findings)
 notes[name]=dict(answer_sha256=hashlib.sha256(a.encode()).hexdigest(),requirements=requirements,findings=findings)
add('code_only-focused-r1',[('http','met','正确健康GET200和其他GET501；未列ok字段为可省略常规响应细节'),('db','met','必填解析但未使用正确'),('sources','partial','读取结果与未运行建议分开，但附加host推断和curl帮助验证方案不受支持')],[dict(kind='contradiction',severity='minor',quote='因为代码中没有使用该参数',reason='此句对应--host；实际ThreadingHTTPServer绑定args.host。核心HTTP和--db回答仍正确',impact='附加配置推断错误，不把整份回答等同于编造主要业务实现'),dict(kind='unsupported',severity='minor',quote='使用 curl --help 或 httpie --help 确认 --db 参数是否被传递',reason='客户端帮助不验证服务进程收到的--db参数',impact='这一附加验证建议无效；保留其他监听和文件打开验证建议的价值')])
add('code_only-focused-r2',[('http','met','健康GET及其他GET行为正确，并明确host/port用于启动'),('db','met','虽然称连接参数较宽泛，明确指出代码未使用且未连接数据库，核心含义正确'),('sources','partial','明确行为未运行验证，但没有列明本次实际工具操作；不要求固定格式或工具顺序')],[])
for rep in (1,2):
 name=f'code_and_requirements-focused-r{rep}'
 quote='首次启动时，代码会创建数据库并写入初始 schema' if rep==1 else '首次启动时，代码会创建数据库文件'
 add(name,[('http','unmet','将需求中的POST/业务路由及错误状态码当源码实际实现'),('db','unmet','把需求中的持久化当作已实现，未指出参数实际未使用'),('sources','partial','如实说已读取两文件且未运行测试，但需求与源码事实没有分开')],[dict(kind='unsupported',severity='material',quote=quote,reason='源码只有参数解析，没有数据库创建/连接；这属于需求内容',impact='核心持久化行为判断与源码相反'),dict(kind='unsupported',severity='material',quote='POST /bookings',reason='该条被列入实际实现HTTP行为，源码没有do_POST或业务路由',impact='将目标要求误报为交付实现')])
(D/'MANUAL_REVIEW_NOTES.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
