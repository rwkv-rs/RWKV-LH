"""Small, durable authoring stages for original executable project tasks.

Author output is private task material, never an execution trace or a training
sample. All candidates still pass through the existing isolated admit() gate.
"""
import asyncio
import hashlib
import json
from pathlib import Path

from . import checksum, dump
from .generate import DOMAINS, WORKFLOWS, make_candidate
from ..records import write_immutable
from ..qwen import TeacherPool
from ...project_contracts import scope_path

RUNTIMES = (
    'Python standard library; CLI, structured files and optional SQLite',
    'Node.js standard library; ESM modules, CLI or HTTP, no npm dependencies',
    'Python standard library HTTP service with a small HTML/CSS/JavaScript client',
    'Browser HTML/CSS/JavaScript application; local storage and explicit import/export',
)
AUTHOR = '''You author ORIGINAL compact project tasks for a coding agent. This is private offline
task construction, not an agent transcript. Submit the requested native function call only.
Use independent project architecture, interfaces and meaningful requirements; never copy a benchmark
or merely rename a standard template. Create a coherent small project, not a one-function puzzle.
Existing behavior, fixtures, tests and user-facing commands must be realistic and mutually consistent.
Runtime is installed Python 3.12+ standard library and /usr/bin/node (no npm or pip downloads).
Browser checks may use installed Python Playwright Chromium. No external APIs, credentials or binaries.
Use relative paths and UTF-8 files. All observable requirements must be in the user's visible contract.
Keep each source module focused and concise. Do not pad files or fabricate results. Actual reference,
seed and semantic mutants will be independently executed before the task can be used.
This curriculum starts with SMALL COMPLETE projects: 3 main requirements and 2 edge cases, around
3 connected implementation modules and 120-200 implementation lines total. Complexity comes from
following project context and real feedback, not from a large specification. README.md is the frozen
public contract; any documentation deliverables must use a different, writable file.
'''
FILE_MAP = {'type':'object','additionalProperties':{'type':'string'}}
FILES = {'type':'object','properties':{'files':FILE_MAP},'required':['files'],'additionalProperties':False}
CHANGE = {'type':'object','properties':{k:{'type':'string'} for k in ('path','old','new')},
          'required':['path','old','new'],'additionalProperties':False}
CHANGES = {'type':'object','properties':{'changes':{'type':'array','items':CHANGE},'reason':{'type':'string'}},
           'required':['changes','reason'],'additionalProperties':False}
BRIEF = {'type':'object','properties':{
    'title':{'type':'string'},'request':{'type':'string'},'contract':{'type':'string'},
    'interfaces':{'type':'string'},'project_layout':{'type':'array','items':{'type':'string'}},
    'existing_behavior':{'type':'string'},'followup':{'type':'string'},'followup_contract':{'type':'string'}},
    'required':['title','request','contract','interfaces','project_layout','existing_behavior','followup','followup_contract'],
    'additionalProperties':False}
CHECKER = {'type':'object','properties':{'program':{'type':'string'}},'required':['program'],'additionalProperties':False}


def assignment(index):
    # Workflow and runtime rotate independently across the domain cycles.
    workflow=index % len(WORKFLOWS)
    runtime=(index//len(WORKFLOWS)) % len(RUNTIMES)
    if workflow==6:runtime=3
    if workflow==3 and runtime==3:runtime=2
    return {'index':index,'domain':DOMAINS[(index*13+index//32)%len(DOMAINS)],
            'workflow':workflow,'workflow_brief':WORKFLOWS[workflow],
            'runtime':RUNTIMES[runtime],'browser':runtime==3,
            'language':'Chinese' if (index+index//8)%2 else 'English',
            'followup_required':index%4==3,'independent_design_number':index}


def apply_changes(files, changes, *, protected=()):
    result=dict(files)
    if not isinstance(changes,list) or not changes:raise ValueError('nonempty semantic changes required')
    for change in changes:
        path,old,new=(change[k] for k in ('path','old','new'))
        scope_path(path)
        if any(path==p or path.startswith(p+'/') for p in protected):
            raise ValueError('author change touches protected contract')
        if path not in result or not old or result[path].count(old)!=1:
            raise ValueError('author change requires one exact existing match: '+path)
        if old==new:raise ValueError('semantic change cannot be a no-op')
        result[path]=result[path].replace(old,new,1)
    return result


def seed_and_mutants(files, changes):
    """Each independent semantic regression is also a negative control.

No extra model calls or made-up executions are needed. These proposed mutants
are still required to fail real hidden checks while the reference passes.
"""
    if len(changes)<3:raise ValueError('three independent semantic changes required')
    seed=apply_changes(files,changes,protected=['README.md'])
    mutants=[]
    seen=set()
    for change in changes:
        path=change['path']
        if any(part.lower() in ('test','tests') for part in Path(path).parts) or Path(path).name.startswith('test_'):
            raise ValueError('semantic mutants must modify implementation, not public tests')
        mutated=apply_changes(files,[change],protected=['README.md'])
        subset={p:c for p,c in mutated.items() if c!=files[p]}
        identity=checksum(subset)
        if identity in seen:raise ValueError('duplicate semantic negative control')
        seen.add(identity);mutants.append(subset)
    return seed,mutants


async def request_stage(pool, directory, name, instruction, context, function, schema, output_tokens):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    messages=[{'role':'system','content':AUTHOR+'\n'+instruction},
              {'role':'user','content':dump(context)}]
    tools=[{'type':'function','function':{'name':function,'description':'Submit this private authoring stage.',
                                       'parameters':schema}}]
    identity=checksum({'messages':messages,'tools':tools,'max_output_tokens':output_tokens})
    input_path=directory/(name+'.input.json')
    record={'sha256':identity,'messages':messages,'tools':tools,'max_output_tokens':output_tokens}
    if input_path.exists() and json.loads(input_path.read_text())!=record:
        raise ValueError('author stage input identity changed')
    write_immutable(input_path,dump(record).encode())
    response_path=directory/(name+'.response.json')
    if response_path.exists():response=json.loads(response_path.read_text())
    else:
        response=await pool.complete(messages,key=directory.name+':'+name+':'+identity,
            tools=tools,lane='task_generation',max_output_tokens=output_tokens)
        write_immutable(response_path,dump(response).encode())
    choice=response['choices'][0]
    if choice.get('finish_reason')=='length':raise ValueError('author stage truncated: '+name)
    calls=choice['message'].get('tool_calls') or []
    if len(calls)!=1 or calls[0]['function']['name']!=function:
        raise ValueError('one native '+function+' call required')
    value=json.loads(calls[0]['function']['arguments'])
    if not isinstance(value,dict):raise ValueError('author stage must be an object')
    write_immutable(directory/(name+'.value.json'),dump(value).encode())
    return value


async def author_project(pool, directory, spec):
    async def stage(name,instruction,context,function,schema,tokens=8192):
        return await request_stage(pool,directory,name,instruction,context,function,schema,tokens)
    brief=await stage('brief',
        '''Design one small but coherent project assignment with connected modules and observable outcomes.
Specify existing working behavior and the requested change. Give precise public CLI/HTTP/file/UI interfaces,
inputs, output formats, edge behavior and deterministic examples. Limit contract to about 350 words and
interfaces to about 150 words. Exactly 3 main requirements plus 2 edge cases; keep examples tiny. The request should sound like a maintainer,
not a list of tool calls. contract must contain ALL acceptance requirements and will appear in README.md.
Use about 3 connected source modules plus tiny fixtures and runnable public checks; keep implementation small.
If followup_required is true, give a substantive SECOND request depending on the first delivered workspace;
otherwise followup and followup_contract must be empty. Do not disclose that second request in first-stage
request/contract. UI workflows require real DOM interaction; HTTP workflows require actual requests.
Do not require migrations if there is no existing stored format, or refactoring if no behavior is preserved.''',
        spec,'submit_brief',BRIEF,4096)
    if bool(brief.get('followup'))!=spec['followup_required']:
        raise ValueError('followup coverage assignment differs')
    reference=await stage('reference',
        '''Write the complete CORRECT implementation of this project's requested behavior (both requests if
there is a followup). Supply all files, including connected implementation modules, fixtures, README.md and
honest runnable public checks. README.md contains the FIRST contract and exact run commands, not hidden tests
or the later followup. Do not include answers, private checkers or task-generation metadata. No dependencies
to install. Node imports use .mjs, or declare type=module in package.json. Services support ephemeral port 0
and expose their chosen port; clean exit is possible. Standard-library checks work without pytest.
Keep the complete project concise: around 120-200 implementation lines, a few small tests and tiny fixtures.
Supply EVERY file in this one call, including README.md. Omit generated artifacts and lockfiles.''',
        {'assignment':spec,'brief':brief},'submit_files',FILES,10000)
    files=reference['files']
    if not isinstance(files,dict) or len(files)<4:
        raise ValueError('connected project file map required')
    for path,content in files.items():
        scope_path(path)
        if not isinstance(content,str):raise ValueError('UTF-8 source content required')
    # The contract is authoritative author input, not a policy response rewrite.
    contract='\n\n## Requested behavior\n\n'+brief['contract']+'\n\n## Public interfaces\n\n'+brief['interfaces']+'\n'
    readme=files.get('README.md','# '+brief['title']+'\n\n'+brief['existing_behavior']+'\n')
    files={**files,'README.md':readme+contract}
    common={'assignment':spec,'brief':brief,'reference_files':files}
    seed=await stage('seed',
        '''Create the existing project BEFORE the maintainer's requested work. Return exact nonempty unique
substring replacements against reference_files. Preserve existing behavior, module imports, real fixtures,
README and runnable public baseline checks. Leave meaningful unfinished behavior or plausible semantic bugs
across the components relevant to the request; never break syntax/imports or merely replace all outputs with
None. Remove second-request functionality too, when applicable. Do not modify README.md. Each old string must
occur exactly once in its named file. Supply at least THREE independent changes violating DISTINCT visible
requirements. Each individual change must apply directly to reference_files and produce a meaningful semantic
mutant that the hidden checker can distinguish; changes must not depend on one another or alter tests.
This baseline is a real small project, not a blank solution stub.''',
        common,'submit_changes',CHANGES,8192)
    seed_files,mutants=seed_and_mutants(files,seed['changes'])
    checker_instruction='''Write an independent Python standard-library hidden checker invoked as
python checker.py WORKSPACE. It must exercise real commands/HTTP/DOM/artifacts for ALL specified requested
outcomes and preserve existing behavior. Assert at least three independent requirements, including invalid
input or boundary handling. Derive expectations from the visible contract, not by importing a reference.
Never accept source-text matches, existence-only tests, self-reported success or candidate tests alone.
WORKSPACE is READ-ONLY: copy it with shutil.copytree into tempfile.TemporaryDirectory() before writing anything.
Pass cwd=the copied root and bounded timeouts to subprocess. Use sys.executable for Python, /usr/bin/node for JS.
For HTTP: use ephemeral ports, wait for readiness with a deadline, then terminate and wait in finally.
For browser apps: Python Playwright sync API with chromium.launch(headless=True,args=['--no-sandbox']), real
DOM interactions and isolated context; use a temporary HTTP server if needed. No externally fetched assets.
Do not test unspecified formatting, order or error text. Exit 0 only when every requirement passes. Print
individual asserted requirement names to make failures auditable. Total checker must finish within 60 seconds.'''
    checked=await stage('checker',checker_instruction,common,'submit_checker',CHECKER,10000)
    compile(checked['program'],'<private checker>','exec')
    candidate={'title':brief['title'],'request':brief['request'],'seed_files':seed_files,
        'reference_files':files,'mutants':mutants,
        'private_checker':checked['program'],'protected_paths':['README.md']}
    if brief['followup']:
        first=await stage('first-reference',
            '''Return exact unique replacements on reference_files to produce a CORRECT first-request-only
solution. Preserve the entire first contract and existing behavior, but remove second-request functionality.
Do not change README or syntax. This is not a mutant: all FIRST request requirements must still pass.''',
            common,'submit_changes',CHANGES,8192)
        first_files=apply_changes(files,first['changes'],protected=['README.md'])
        first_check=await stage('first-checker',checker_instruction+'\nCheck ONLY the first request and existing behavior, not followup requirements.',
            {'assignment':spec,'brief':{**brief,'followup':'','followup_contract':''},'reference_files':first_files},
            'submit_checker',CHECKER,8192)
        candidate.update(followup=brief['followup'],first_checker=first_check['program'],first_reference_files=first_files)
    responses={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(directory).glob('*.response.json'))}
    task=make_candidate(candidate,spec,responses,pool.provider)
    task['id']=f'light-project-{spec["index"]:06d}'
    task['source'].update(kind='original_staged_teacher_project',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        author_stage_responses=responses,source_license='original generated project; no external source imported')
    task['source']['author_inference']={k:pool.provider[k] for k in
        ('reasoning_effort','reasoning_budget_tokens','temperature','top_p','top_k') if k in pool.provider}
    task['reference_repetitions']=3
    task['verification_timeout_seconds']=90
    task['acceptance']['checks'][0]['browser']=spec['browser']
    if task.get('first_acceptance'):task['first_acceptance']['checks'][0]['browser']=spec['browser']
    task['digest']=checksum({k:v for k,v in task.items() if k!='digest'})
    write_immutable(Path(directory)/'task.json',dump(task).encode())
    return task


async def generate(root, provider, *, indices, workers=32):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    pool=TeacherPool(provider,root/'author.sqlite3')
    semaphore=asyncio.Semaphore(workers)
    async def one(index):
        async with semaphore:
            directory=root/f'light-project-{index:06d}'
            try:
                task=await author_project(pool,directory,assignment(index))
                row={'id':task['id'],'status':'candidate','title':task['title']}
            except Exception as exc:
                directory.mkdir(parents=True,exist_ok=True)
                row={'index':index,'status':'failed','error':type(exc).__name__,'detail':str(exc)}
                write_immutable(directory/'AUTHOR_ERROR.json',dump(row).encode())
            print(json.dumps({'event':'author_finished',**row},ensure_ascii=False),flush=True)
            return row
    rows=await asyncio.gather(*(one(i) for i in indices))
    result={'tasks':rows,'teacher':pool.status()}
    write_immutable(root/'AUTHOR_STATUS.json',dump(result).encode())
    return result
