"""Lossless normalization into a separate CC-view training data entrance.

No Project Executor loader imports this module. Unresolved conversions block
freezing; they are never quietly reclassified as low-quality source records.
"""
from copy import deepcopy
import ast
import hashlib
import json
import re

from . import cc_view_experiment as cc
from .statetune_episodes import ROW_SCHEMA, equal_chunk_starts, validate_row

DATASET_SCHEMA='rwkv-lh.cc-view-training-dataset.v1'


class FilteredTrajectory(ValueError):
    """Only a preregistered owner filter can produce this outcome."""


class ConversionPending(ValueError):
    """Preserve the source and block admission until its conversion is resolved."""


def exported_json(text):
    """Recover export-only JSON escaping without changing a decoded payload."""
    try:
        return json.loads(text,strict=False)
    except json.JSONDecodeError:
        # These sequences are not valid JSON escapes at all. Treat the original
        # slash literally; valid escapes and all content characters stay intact.
        pieces=[];index=0
        while index<len(text):
            if text[index]!='\\':pieces.append(text[index]);index+=1;continue
            end=index
            while end<len(text) and text[end]=='\\':end+=1
            count=end-index
            invalid=(end==len(text) or text[end] not in '"\\/bfnrtu'
                     or text[end]=='u' and not re.match(r'[0-9a-fA-F]{4}',text[end+1:end+5]))
            pieces.append('\\'*(count+int(bool(count%2 and invalid))))
            index=end
        repaired=''.join(pieces)
        try:return json.loads(repaired,strict=False)
        except json.JSONDecodeError as error:
            try:
                value=ast.literal_eval(text)
                if isinstance(value,(list,dict,str,int,float,bool,type(None))):return value
            except (ValueError,SyntaxError,TypeError):pass
            raise ConversionPending('ambiguous_export_json: '+str(error)) from error


def _forbidden(name):
    lowered=name.lower()
    return (lowered in {'agent','webfetch','fetch','websearch','mmode','agentic_fetch',
                        'enterplanmode','exitplanmode','sourcegraph','fetch_url'}
            or lowered.startswith('lsp_'))


def source_turn(text):
    think=None;body=text
    if body.startswith('<think>'):
        if '</think>' not in body:
            raise ConversionPending('unclosed_source_think')
        think,body=body[len('<think>'):].split('</think>',1)
    stripped=body.strip()
    opening=body.find('<tool_calls>')
    if opening>=0 and stripped.endswith('</tool_calls>'):
        narration=body[:opening]
        framed=body[opening:].strip()
        inner=framed[len('<tool_calls>'):-len('</tool_calls>')]
        blocks=re.split(r'</tool_calls>\s*<tool_calls>',inner)
        carrier=[]
        for block in blocks:
            batch=exported_json(block)
            if not isinstance(batch,list):raise ConversionPending('invalid_source_tool_carrier')
            carrier.extend(batch)
        if not isinstance(carrier,list) or not carrier:
            raise ConversionPending('invalid_source_tool_carrier')
        calls=[]
        for call in carrier:
            function=call.get('function',call)
            name=function.get('name')
            if not isinstance(name,str):raise ConversionPending('source_tool_name_missing')
            arguments=function.get('arguments',{})
            if isinstance(arguments,str):arguments=exported_json(arguments)
            if not isinstance(arguments,dict):raise ConversionPending('source_arguments_not_object')
            calls.append((name,arguments))
        return dict(think=think,calls=calls,summary=None,narration=narration)
    if '<tool_calls>' in body or '</tool_calls>' in body:
        raise ConversionPending('source_tool_prelude_or_ambiguous_framing')
    if not stripped:raise ConversionPending('source_turn_has_no_action_or_final')
    return dict(think=think,calls=[],summary=body,narration='')


def original_request(text):
    text=re.sub(r'<(?:system[-_]reminder|turn_meta)\b[^>]*>.*?</(?:system[-_]reminder|turn_meta)>','',text,flags=re.S|re.I)
    return text.strip()


def workspace_roots(messages):
    roots=[]
    for message in messages:
        if 'System' not in message:continue
        for match in re.finditer(r'(?im)working directory:\s*([^\r\n<]+)',message['System']):
            root=match[1].strip().rstrip('/\\')
            if root and root not in roots:roots.append(root)
    if not roots:
        # A source with no system header can still explicitly report its cwd.
        for message in messages:
            for match in re.finditer(r'<cwd>(.*?)</cwd>',message.get('🐱',''),re.S):
                root=match[1].strip().rstrip('/\\')
                if root:roots.append(root);break
            if roots:break
    return roots


def replace_roots(value,roots):
    if isinstance(value,str):
        for root in sorted(roots,key=len,reverse=True):
            for variant in dict.fromkeys((root,root.replace('\\','/'),root.replace('/','\\'))):
                value=value.replace(variant,'.')
        return value
    if isinstance(value,list):return [replace_roots(item,roots) for item in value]
    if isinstance(value,tuple):return tuple(replace_roots(item,roots) for item in value)
    if isinstance(value,dict):return {key:replace_roots(item,roots) for key,item in value.items()}
    return value


def normalize_call(name,arguments):
    """Named dialect mappings; no invented command, code, path or model step."""
    aliases={'bash':'Bash','exec_shell':'Bash','write':'Write','write_file':'Write','edit':'Edit','edit_file':'Edit',
             'multiedit':'MultiEdit','read':'Read','view':'Read','read_file':'Read',
             'ls':'LS','list_dir':'LS','glob':'Glob','grep':'Grep','grep_files':'Grep',
             'job_output':'JobOutput','job_kill':'JobKill','TaskOutput':'JobOutput','TaskStop':'JobKill',
             'todos':'TaskUpdate','todo':'TaskUpdate','checklist_write':'TaskUpdate','todowrite':'TaskUpdate',
             'exec_shell_wait':'JobOutput'}
    canonical=aliases.get(name,name);args=deepcopy(arguments)
    if canonical not in {'Read','Write','Edit','MultiEdit','Bash','BashBackground','JobOutput','JobKill','Glob','Grep','LS','TaskCreate','TaskUpdate','TaskList'}:
        raise ConversionPending('unmapped_tool: '+name)
    renames={'filePath':'file_path','oldString':'old_string','newString':'new_string',
             'working_dir':'cwd','workdir':'cwd','working_directory':'cwd','shell_id':'task_id',
             'task_id':'task_id','file_offset':'offset','start_line':'offset','max_lines':'limit',
             'background':'run_in_background'}
    if canonical in {'Read','Write','Edit','MultiEdit'}:renames.update(path='file_path')
    if canonical=='Edit':renames.update(old='old_string',new='new_string',all='replace_all',search='old_string',replace='new_string')
    if canonical=='Bash':renames.update(cmd='command',timeout_ms='timeout')
    if canonical=='TaskUpdate' and 'todos' in args:
        items=[]
        for item in args['todos']:
            converted={({'content':'subject','text':'subject','active_form':'activeForm'}.get(key,key)):value for key,value in item.items()}
            if 'id' in converted:converted['id']=str(converted['id'])
            items.append(converted)
        args={'todos':items}
    converted={}
    for key,value in args.items():
        target=renames.get(key,key)
        if target in converted and converted[target]!=value:
            raise ConversionPending('conflicting_source_argument_aliases: '+name+'/'+target)
        converted[target]=value
    args=converted
    for key in ('offset','limit','depth','head_limit','wait_timeout'):
        if isinstance(args.get(key),str) and re.fullmatch(r'[0-9]+',args[key]):args[key]=int(args[key])
    if canonical=='Grep' and 'include' in args:
        if isinstance(args['include'],str):args['include']=[args['include']]
    if canonical=='MultiEdit':
        if isinstance(args.get('edits'),str):args['edits']=exported_json(args['edits'])
        if 'edits' not in args and {'old_string','new_string'}<=args.keys():
            args['edits']=[{key:args.pop(key) for key in ('old_string','new_string','replace_all') if key in args}]
        if isinstance(args.get('edits'),list):
            entries=[]
            for item in args['edits']:
                if isinstance(item,(tuple,list)) and len(item)==2 and all(isinstance(v,str) for v in item):
                    item={'old_string':item[0],'new_string':item[1]}
                if not isinstance(item,dict):raise ConversionPending('unresolved_multiedit_entry_representation')
                entries.append(item)
            args['edits']=[{({'path':'file_path','filePath':'file_path','old':'old_string','new':'new_string',
                              'oldString':'old_string','newString':'new_string','all':'replace_all'}.get(k,k)):v for k,v in item.items()}
                           for item in entries]
    if canonical=='LS' and isinstance(args.get('ignore'),str):args['ignore']=[args['ignore']]
    if canonical=='Read' and 'receipt_id' not in args:
        args['offset_unit']='lines';args['limit_unit']='lines'
    if canonical=='Bash':
        if isinstance(args.get('timeout'),str):args['timeout']=float(args['timeout'])
        if 'timeout' in args and (name=='Bash' or 'timeout_ms' in arguments):
            args['timeout']=args['timeout']/1000
        if args.pop('run_in_background',False):canonical='BashBackground'
    if canonical in {'JobOutput','JobKill'}:
        for old in ('taskId','id','session_id'):
            if old in args:args['task_id']=str(args.pop(old))
        args.pop('block',None) if canonical=='JobKill' else None
        if 'block' in args:args['wait']=args.pop('block')
        if 'timeout' in args:args['wait_timeout']=args.pop('timeout')/1000
    if canonical=='TaskUpdate' and 'taskId' in args:args['taskId']=str(args['taskId'])
    return canonical,args


def _identical_actions(turns):
    prior=None;chain=0
    for turn in turns:
        for name,args in turn['calls']:
            key=json.dumps([name,args],sort_keys=True,ensure_ascii=False,separators=(',',':'))
            chain=chain+1 if key==prior else 1;prior=key
            if chain>=3:return True
    return False


def _feedback(text):
    # Exported results are already individually framed. Keep the whole literal
    # contents, including newlines; never summarize or manufacture tool results.
    stripped=text.strip()
    if stripped.startswith('<tool_result>') and stripped.endswith('</tool_result>'):
        bodies=re.split(r'</tool_result>\s*<tool_result>',stripped[len('<tool_result>'):-len('</tool_result>')])
        return dict(tool_results=bodies)
    return dict(user_message=text)


def convert_official(messages,definitions):
    """Normalize one entire original trajectory or return an explicit blocker/filter."""
    parsed=[];forbidden=[]
    for index,message in enumerate(messages):
        if '🤖' in message:
            # A lost argument export must not hide a separately named forbidden
            # function. Quoted file payloads have escaped keys, not these carriers.
            names=re.findall(r'"function"\s*:\s*\{\s*"name"\s*:\s*"([^"\\]+)"',message['🤖'])
            forbidden.extend(name for name in names if _forbidden(name))
            try:
                turn=source_turn(message['🤖']);parsed.append((index,turn))
                forbidden.extend(name for name,_ in turn['calls'] if _forbidden(name))
            except ConversionPending as error:
                parsed.append((index,dict(think=None,calls=[],summary=None,narration='',
                    source_context=message['🤖'],context_reason=str(error))))
    if forbidden:raise FilteredTrajectory('forbidden_tool: '+','.join(sorted(set(forbidden))))
    user_index=next((index for index,msg in enumerate(messages) if '🐱' in msg),None)
    if user_index is None:raise ConversionPending('source_original_request_missing')
    roots=workspace_roots(messages)
    request=replace_roots(original_request(messages[user_index]['🐱']),roots)
    turns=[]
    for index,raw in parsed:
        if index<=user_index:raise ConversionPending('assistant_precedes_original_request')
        turn=replace_roots(raw,roots)
        mark=True
        if 'source_context' in turn:
            target=turn['source_context'];mark=False
        else:
            try:
                normalized=[normalize_call(name,args) for name,args in turn['calls']]
                target=cc.render_target(definitions=definitions,**{**turn,'calls':normalized})
                turn['calls']=normalized
            except (ValueError,KeyError,TypeError) as error:
                # Preserve an unrepresentable source action in its original
                # place. It cannot be a valid CC decoder target and must not
                # teach a fake parameter or an invented replacement operation.
                target=replace_roots(messages[index]['🤖'],roots);mark=False
                turn['context_reason']='noncanonical_source_action: '+str(error)
        prior_index=parsed[len(turns)-1][0] if turns else user_index
        if turns:
            user_messages=[replace_roots(msg['🐱'],roots) for msg in messages[prior_index+1:index] if '🐱' in msg]
            if not user_messages:raise ConversionPending('missing_source_feedback_between_turns')
            kwargs=_feedback('\n\n'.join(user_messages))
            prompt=cc.build_input(definitions=definitions,**kwargs)
        else:prompt=cc.build_input(definitions=definitions,context=request,todos=[])
        turns.append({**turn,'target':target,'prompt':prompt,'supervised':mark})
    if _identical_actions(turns):raise FilteredTrajectory('three_identical_actions')
    return dict(request=request,roots=roots,turns=turns,
                has_ending=bool(turns and turns[-1]['summary'] is not None),
                source_messages=len(messages),payload_roundtrip_verified=True,
                context_only_turns=[dict(index=i,reason=t['context_reason']) for i,t in enumerate(turns) if not t['supervised']])


def convert_executor_episode(row,definitions,tokenizer):
    """Re-render the complete frozen A transcript, retaining every target and mask."""
    spans=row['target_spans'];tokens=row['token_ids'];turns=[]
    initial=tokenizer.decode_bytes(tokens[1:spans[0][0]]).decode('utf-8')
    context=cc.context_from_a_prompt(initial);todos=cc.todos_from_context(context)
    request=dict(cc.top_sections(context)).get('original_request','')
    for index,((start,count),mark) in enumerate(zip(spans,row['supervised'])):
        command=json.loads(tokenizer.decode_bytes(tokens[start:start+count]).decode('utf-8'))
        target=cc.native_to_cc(command)
        try:parsed=cc.parse_output(target,definitions)
        except (ValueError,KeyError) as error:raise ConversionPending('self_target_conversion: '+str(error)) from error
        if index:
            prior_start,prior_count=spans[index-1]
            delta=tokenizer.decode_bytes(tokens[prior_start+prior_count:start]).decode('utf-8')
            prompt=cc.build_input(definitions=definitions,tool_results=[cc.result_from_a_delta(delta)],
                                  remaining=cc.remaining_from_a_prompt(delta))
        else:prompt=cc.build_input(definitions=definitions,context=context,todos=todos.visible(),
                                  remaining=cc.remaining_from_a_prompt(initial))
        target=cc.render_target(definitions=definitions,calls=parsed.calls,summary=parsed.summary,think=None)
        turns.append(dict(think=None,calls=list(parsed.calls),summary=parsed.summary,target=target,prompt=prompt,supervised=mark))
    if _identical_actions(turns):raise FilteredTrajectory('three_identical_actions')
    return dict(request=request,roots=[],turns=turns,has_ending=bool(turns and turns[-1]['summary'] is not None),
                payload_roundtrip_verified=True,original_supervised=list(row['supervised']))


def episode_row(converted,*,episode_id,source,tokenizer,max_chunk_tokens=16384):
    ids=[0];spans=[];marks=[];actions=[];categories=[];mask_audit=[]
    for turn in converted['turns']:
        ids.extend(tokenizer.encode(turn['prompt']))
        target=tokenizer.encode(turn['target']);start=len(ids);ids.extend(target)
        text=turn['target'];ranges=[];think_body=None
        if turn['think'] is not None:
            body_end=7+len(turn['think'].encode());think_end=body_end+len('</think>')
            ranges.append((0,think_end,'Think'));think_body=(7,body_end)
        else:think_end=0
        if not turn['supervised']:
            ranges=[(0,len(text.encode()),'source_context')]
        elif turn['summary'] is not None:ranges.append((think_end,len(text.encode()),'finish'))
        else:
            opening=text.find('<tool_calls>')
            if opening>0:ranges.append((think_end,len(text[:opening].encode()),'Narration'))
            cursor=opening+len('<tool_calls>[');decoder=json.JSONDecoder()
            while cursor<len(text) and text[cursor]!=']':
                item,end=decoder.raw_decode(text,cursor)
                ranges.append((len(text[:cursor].encode()),len(text[:end].encode()),item['function']['name']))
                cursor=end+(text[end:end+1]==',')
        byte_spans=[];offset=0
        for token in target:
            end=offset+len(tokenizer.idx2token[token]);byte_spans.append((offset,end));offset=end
        if offset!=len(text.encode()):raise ConversionPending('target_tokenizer_byte_roundtrip_failed')
        thought_tokens=sum(end>think_body[0] and begin<think_body[1] for begin,end in byte_spans) if think_body else 0
        long_thought=thought_tokens>cc.THINK_LIMIT
        if long_thought:mask_audit.append(dict(turn=len(categories),reason='source_think_exceeds_live_cap_preserved_as_context',tokens=thought_tokens))
        for index,(begin,end) in enumerate(byte_spans):
            category=next((name for a,b,name in ranges if end>a and begin<b),'Format')
            supervised=bool(turn['supervised']) and not (long_thought and category=='Think')
            position=start+index
            if spans and sum(spans[-1])==position and marks[-1]==supervised and actions[-1]==category:
                spans[-1][1]+=1
            else:spans.append([position,1]);marks.append(supervised);actions.append(category)
        categories.append(dict(action='finish' if turn['summary'] is not None else '|'.join(n for n,_ in turn['calls']),
                               think_present=turn['think'] is not None,source_think_tokens=thought_tokens,
                               source_supervised=turn['supervised'],context_reason=turn.get('context_reason')))
    row=dict(schema_version=ROW_SCHEMA,input_protocol=cc.PROTOCOL,episode_id=episode_id,
             source=source,request_sha256=hashlib.sha256(converted['request'].encode()).hexdigest(),
             token_ids=ids,target_spans=spans,supervised=marks,actions=actions,
             chunk_starts=equal_chunk_starts(len(ids)-1,max_chunk_tokens),categories=categories,
             has_ending=converted['has_ending'],mask_audit=mask_audit)
    validate_row(row,context_tokens=max_chunk_tokens,vocab_size=65536,bos_token_id=0)
    return row
