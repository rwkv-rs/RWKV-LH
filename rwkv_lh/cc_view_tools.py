"""CC-view tool extensions, registered only on the opt-in experiment harness."""
from copy import deepcopy
import fnmatch
import json
from pathlib import Path

from .harness import ActionDefinition, ActionResult


def _object(properties, required=()):
    return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}


def additional_definitions(*, background):
    text={'type':'string'}
    path={'type':'string','minLength':1,'pattern':r'^(?:[^\s/]|\s+\S)'}
    edit=_object({'file_path':path,'old_string':text,'new_string':text,'replace_all':{'type':'boolean'}},
                 ('old_string','new_string'))
    rows=[('LS','List directory entries; recursive is optional.',
           _object({'path':path,'recursive':{'type':'boolean'},'max_entries':{'type':'integer','minimum':1,'maximum':1024}},())),
          ('MultiEdit','Apply all exact edits to one file atomically; a failed edit publishes nothing.',
           _object({'file_path':path,'edits':{'type':'array','items':edit,'minItems':1}},('edits',)))]
    if background:
        rows.extend([
            ('BashBackground','Start a run-owned Bash job on an isolated workspace snapshot. Changes publish on completed JobOutput; conflicting edits are rejected.',
             _object({'command':{'type':'string','minLength':1},'cwd':path,
                      'timeout':{'type':'number','exclusiveMinimum':0,'maximum':3600},
                      'stdin':text,'description':text,
                      'env':{'type':'object','properties':{},'required':[], 'additionalProperties':text}},('command',))),
            ('JobOutput','Read live stdout/stderr for a job owned by this run. wait waits until completion or wait_timeout seconds (default ten).',
             _object({'task_id':{'type':'string','minLength':1},'wait':{'type':'boolean'}},('task_id',))),
            ('JobKill','Stop a job owned by this run and retain its receipt.',
             _object({'task_id':{'type':'string','minLength':1}},('task_id',))),
        ])
    return [{'type':'function','function':{'name':name,'description':description,'parameters':schema}}
            for name,description,schema in rows]


def extend_catalog(definitions):
    """Explicit units keep source line cursors distinct from native byte cursors."""
    for entry in definitions:
        name=entry['function']['name'];schema=entry['function']['parameters'];props=schema['properties']
        for key in ('file_path','path','cwd'):
            if key in props:
                # The execution harness owns normalization and path authority.
                # A literal /workspace alias is valid in its sandbox as well.
                props[key]={'type':'string','minLength':1}
        if name=='Read':
            schema['required']=[]
            props['receipt_id']={'type':'string','minLength':1}
            props['offset_unit']={'type':'string','enum':['bytes','lines']}
            props['limit_unit']={'type':'string','enum':['tokens','lines']}
            props['limit']={'type':'integer','minimum':1}
            entry['function']['description']='Read UTF-8 text by file_path, or read a previous run-owned tool receipt by receipt_id instead. Defaults: offset in bytes, limit in tokens. Explicit offset_unit=lines and limit_unit=lines preserve line-based source calls; line offsets are one-based (zero also starts at the first line).'
        if name=='Glob':
            props['pattern']={'type':'string','minLength':1}
            entry['function']['description']='Find workspace paths matching a relative glob pattern under path; default pattern is *.'
        if name=='Bash':
            props['description']={'type':'string'}
            props['timeout']['maximum']=3600
            props['auto_background_after']={'type':'integer','minimum':0}
        if name=='BashBackground':
            props['auto_background_after']={'type':'integer','minimum':0}
        if name=='JobOutput':
            props['wait_timeout']={'type':'number','minimum':0,'maximum':3600}
        if name=='LS':
            props['depth']={'type':'integer','minimum':0}
            props['ignore']={'type':'array','items':{'type':'string'}}
        if name=='TaskCreate':
            schema['required']=['subject']
        if name=='TaskUpdate':
            schema['required']=[]
            item=_object({'id':{'type':'string'},'subject':{'type':'string'},'description':{'type':'string'},
                          'activeForm':{'type':'string'},'priority':{'type':'string'},
                          'status':{'type':'string','enum':['pending','in_progress','completed']}},('subject','status'))
            props['todos']={'type':'array','items':item}
            props['addBlockedBy']={'type':'array','items':{'type':'string'}}
            props['addBlocks']={'type':'array','items':{'type':'string'}}
        if name=='Grep':
            props.update({'include':{'type':'array','items':{'type':'string'}},'output_mode':{'type':'string','enum':['content','files_with_matches','count']},
                          'glob':{'type':'string'},'head_limit':{'type':'integer','minimum':0},
                          '-n':{'type':'boolean'},'-i':{'type':'boolean'},
                          '-A':{'type':'integer','minimum':0},'-B':{'type':'integer','minimum':0},'-C':{'type':'integer','minimum':0}})
    return definitions


def install(harness, *, jobs=None):
    """Use existing path resolution and outer Project transactions for every extension."""
    def multi(goal,args):
        values={}
        for edit in args['edits']:
            filename=edit.get('file_path',args['path'])
            path=harness.resolve_path(goal,filename,must_exist=True)
            value=values.get(path,path.read_text(encoding='utf-8'))
            old,new=edit['old_string'],edit['new_string'];count=value.count(old)
            if not old or (not edit.get('replace_all',False) and count!=1) or not count:
                raise ValueError('MultiEdit match is missing or ambiguous')
            value=value.replace(old,new) if edit.get('replace_all',False) else value.replace(old,new,1)
            values[path]=value
        for path,value in values.items():
            path.write_text(value,encoding='utf-8')
        return ActionResult('cc_multi_edit',True,output=json.dumps({'files':[
            str(path.relative_to(Path(goal.workspace_root))) for path in values]},ensure_ascii=False))

    def glob(goal,args):
        base=harness.resolve_path(goal,args.get('path','.'),must_exist=True)
        pattern=args.get('pattern','*')
        if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
            raise ValueError('Glob pattern must stay in the workspace')
        found=[]
        for path in sorted(base.glob(pattern)):
            relative=path.relative_to(Path(goal.workspace_root)).as_posix()
            harness.resolve_path(goal,relative,must_exist=True)
            found.append(relative)
        return ActionResult('cc_glob',True,output=json.dumps(found,ensure_ascii=False))

    def read_lines(goal,args):
        path=harness.resolve_path(goal,args['path'],must_exist=True)
        text=path.read_text(encoding='utf-8')
        offset=args.get('offset',0);limit=args.get('limit',2000)
        if args.get('offset_unit','bytes')=='bytes':
            text=text.encode('utf-8')[offset:].decode('utf-8')
        else:
            text=''.join(text.splitlines(keepends=True)[max(0,offset-1):])
        if args.get('limit_unit','tokens')=='lines':
            text=''.join(text.splitlines(keepends=True)[:limit])
        else:
            from .token_budget import smart_truncate
            text,_=smart_truncate(text,limit)
        return ActionResult('cc_read',True,output=text)

    def list_entries(goal,args):
        base=harness.resolve_path(goal,args.get('path','.'),must_exist=True)
        depth=args.get('depth',1);ignore=args.get('ignore',[])
        rows=[]
        for path in sorted(base.rglob('*') if args.get('recursive') or depth!=1 else base.iterdir()):
            relative=path.relative_to(base).as_posix()
            if depth and len(Path(relative).parts)>depth:continue
            if any(fnmatch.fnmatch(relative,p) or any(fnmatch.fnmatch(part,p) for part in Path(relative).parts) for p in ignore):continue
            rows.append(path.relative_to(Path(goal.workspace_root)).as_posix())
            if len(rows)>=args.get('max_entries',1024):break
        return ActionResult('cc_ls',True,output=json.dumps(rows,ensure_ascii=False))

    def grep(goal,args):
        import re
        base=harness.resolve_path(goal,args.get('path','.'),must_exist=True)
        files=([base] if base.is_file() else sorted(
            base.rglob('*') if args.get('recursive',True) else base.iterdir()))
        pattern=re.compile(re.escape(args['pattern']) if args.get('mode')=='literal' else args['pattern'],
                           re.I if args.get('-i') or args.get('case_sensitive') is False else 0)
        found=[];mode=args.get('output_mode','content');limit=args.get('head_limit',args.get('max_results',100))
        for path in files:
            if not path.is_file():continue
            relative=path.relative_to(Path(goal.workspace_root)).as_posix()
            include=args.get('include',args.get('glob'))
            patterns=include if isinstance(include,list) else [include] if include else []
            if patterns and not any(fnmatch.fnmatch(relative,p) or fnmatch.fnmatch(path.name,p) for p in patterns):continue
            harness.resolve_path(goal,relative,must_exist=True)
            try:lines=path.read_text(encoding='utf-8').splitlines()
            except (UnicodeError,OSError):continue
            matches=[index for index,line in enumerate(lines) if pattern.search(line)]
            if not matches:continue
            if mode=='files_with_matches':found.append(relative)
            elif mode=='count':found.append({'path':relative,'count':len(matches)})
            else:
                before=args.get('-B',args.get('-C',0));after=args.get('-A',args.get('-C',0))
                for index in sorted({j for i in matches for j in range(max(0,i-before),min(len(lines),i+after+1))}):
                    found.append({'path':relative,'line':index+1,'text':lines[index]})
            if limit and len(found)>=limit:found=found[:limit];break
        return ActionResult('cc_grep',True,output=json.dumps(found,ensure_ascii=False))

    text={'type':'string'};path={'type':'string','minLength':1}
    edit=_object({'file_path':path,'old_string':text,'new_string':text,'replace_all':{'type':'boolean'}},('old_string','new_string'))
    registrations=[
        ('cc_multi_edit',False,{'path':path,'edits':{'type':'array','items':edit,'minItems':1}},('path','edits'),multi),
        ('cc_glob',True,{'path':path,'pattern':text},(),glob),
        ('cc_read',True,{'path':path,'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1},
                         'offset_unit':{'type':'string','enum':['bytes','lines']},
                         'limit_unit':{'type':'string','enum':['tokens','lines']}},('path',),read_lines),
        ('cc_ls',True,{'path':path,'depth':{'type':'integer','minimum':0},'recursive':{'type':'boolean'},
                       'ignore':{'type':'array','items':text},'max_entries':{'type':'integer','minimum':1}},(),list_entries),
    ]
    for name,readonly,props,required,handler in registrations:
        harness.register_action(ActionDefinition(name,'CC-view '+name,readonly,not readonly,True,30,
            argument_schema=props,required_arguments=required),handler)
    catalog=extend_catalog([{'function':{'name':'Grep','description':'',
        'parameters':_object({'pattern':text,'path':path,'mode':{'type':'string'},'case_sensitive':{'type':'boolean'},
                              'recursive':{'type':'boolean'},'max_results':{'type':'integer','minimum':1}},('pattern',))}}])
    harness.register_action(ActionDefinition('cc_grep','CC-view content search',True,False,True,30,
        argument_schema=catalog[0]['function']['parameters']['properties'],required_arguments=('pattern',)),grep)
    from dataclasses import replace
    definition=harness.definition('run_shell')
    props={**definition.argument_schema,'timeout':{'type':'number','exclusiveMinimum':0,'maximum':3600}}
    harness._definitions['run_shell']=replace(definition,argument_schema=props)
    if jobs is not None:
        common={'path':path,'task_id':text,'wait':{'type':'boolean'},'command':text,'cwd':path,
                'timeout':{'type':'number','exclusiveMinimum':0,'maximum':3600},'stdin':text,
                'description':text,'auto_background_after':{'type':'integer','minimum':0},
                'wait_timeout':{'type':'number','minimum':0,'maximum':3600},
                'env':{'type':'object','additionalProperties':text}}
        handlers={
            'cc_job_start':lambda goal,args:jobs.start(goal,args),
            'cc_job_output':lambda goal,args:jobs.output(goal,args),
            'cc_job_kill':lambda goal,args:ActionResult('cc_job_kill',True,output=json.dumps(jobs.kill(args['task_id']))),
            'cc_bash':lambda goal,args:jobs.foreground(goal,args),
        }
        for name,handler in handlers.items():
            harness.register_action(ActionDefinition(name,'CC-view run-owned background job',False,True,False,30,
                argument_schema=common,required_arguments=('path',),
                side_effect_class='run_owned_process_and_snapshot_publication'),handler)


def native_call(name,arguments,step_id, *, job_authority='.'):
    args=deepcopy(arguments)
    if name=='MultiEdit':
        filename=args.get('file_path',next((edit['file_path'] for edit in args['edits'] if 'file_path' in edit),None))
        if filename is None:raise ValueError('MultiEdit must name a file for each edit')
        return {'function':'execute_tool','params':{'step_id':step_id,'tool':'cc_multi_edit',
                 'arguments':{'path':filename,'edits':args['edits']}}}
    if name=='Glob' and args.get('pattern','*') not in ('*','**/*'):
        return {'function':'execute_tool','params':{'step_id':step_id,'tool':'cc_glob','arguments':args}}
    if name=='LS':
        return {'function':'execute_tool','params':{'step_id':step_id,
                 'tool':'cc_ls' if 'depth' in args or 'ignore' in args else 'list_directory','arguments':args}}
    if name=='Grep' and any(k in args for k in ('include','glob','output_mode','head_limit','-n','-i','-A','-B','-C')):
        return {'function':'execute_tool','params':{'step_id':step_id,'tool':'cc_grep','arguments':args}}
    if name=='Read' and ('offset_unit' in args or 'limit_unit' in args or args.get('limit',256)<256):
        args['path']=args.pop('file_path')
        return {'function':'execute_tool','params':{'step_id':step_id,'tool':'cc_read','arguments':args}}
    if name=='Bash':
        args.pop('description',None)
        if 'auto_background_after' in args:
            return {'function':'execute_tool','params':{'step_id':step_id,'tool':'cc_bash',
                     'arguments':{**args,'path':job_authority}}}
    if name in ('BashBackground','JobOutput','JobKill'):
        operation={'BashBackground':'cc_job_start','JobOutput':'cc_job_output','JobKill':'cc_job_kill'}[name]
        return {'function':'execute_tool','params':{'step_id':step_id,'tool':operation,
                 'arguments':{**args,'path':job_authority}}}
    from .cc_view_experiment import cc_to_native
    return cc_to_native(name,args,step_id=step_id)
