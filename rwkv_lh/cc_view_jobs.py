"""Run-owned, sandboxed background Bash with explicit snapshot publication."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import replace
from uuid import uuid4

from .harness import ActionHarness, ActionResult
from .project_tools import configure_project_tools
from .schema import GoalState, TaskAction
from .workspace_snapshot import copy_verified_workspace, tree_identity


def _write_new(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


class Jobs:
    """Only this object's subprocess handles can be queried or stopped."""
    def __init__(self,directory):
        self.root=Path(directory)
        self.root.mkdir(exist_ok=False)
        self.items={}

    def start(self,goal,arguments):
        identifier='job-'+uuid4().hex
        directory=self.root/identifier
        directory.mkdir()
        before=copy_verified_workspace(goal.workspace_root,directory/'workspace',exclude_git=False)
        args={k:v for k,v in arguments.items() if k not in ('path','description','auto_background_after','wait_timeout')}
        _write_new(directory/'REQUEST.json',dict(request=goal.request,arguments=args,before=before))
        stdout=(directory/'WORKER_STDOUT.log').open('xb');stderr=(directory/'WORKER_STDERR.log').open('xb')
        try:
            process=subprocess.Popen([sys.executable,'-B','-m',__name__,str(directory)],
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
        finally:
            stdout.close();stderr.close()
        self.items[identifier]=dict(process=process,directory=directory,before=before,published=False)
        _write_new(directory/'STARTED.json',dict(pid=process.pid,task_id=identifier,scope='this run'))
        return ActionResult('cc_job_start',True,output=json.dumps(dict(task_id=identifier,status='running')))

    def _item(self,identifier):
        if identifier not in self.items:
            raise ValueError('Unknown job for this run')
        return self.items[identifier]

    def output(self,goal,arguments):
        item=self._item(arguments['task_id']);process=item['process']
        if arguments.get('wait',False) and process.poll() is None:
            try:process.wait(timeout=arguments.get('wait_timeout',10))
            except subprocess.TimeoutExpired:pass
        if process.poll() is None:
            def stream(name):
                path=item['directory']/name
                return path.read_bytes().decode('utf-8',errors='replace') if path.exists() else ''
            return ActionResult('cc_job_output',True,output=json.dumps(dict(task_id=arguments['task_id'],status='running',
                stdout=stream('LIVE_STDOUT.bin'),stderr=stream('LIVE_STDERR.bin')),ensure_ascii=False))
        path=item['directory']/'RESULT.json'
        if not path.exists():
            return ActionResult('cc_job_output',False,output=json.dumps(dict(task_id=arguments['task_id'],status='stopped',exit_code=process.returncode)),
                                error={'type':'BackgroundWorkerStopped','message':'Worker stopped without a completed command receipt'})
        raw=json.loads(path.read_text());result=ActionResult.from_dict(raw)
        if not item['published']:
            staged=item['directory']/'workspace';after=tree_identity(staged,allow_links=True)
            before=item['before'];current=tree_identity(goal.workspace_root,allow_links=True)
            changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
            conflicts=[p for p in changed if current.get(p)!=before.get(p)]
            if conflicts:
                return ActionResult('cc_job_output',False,output=result.output,
                    error={'type':'BackgroundWorkspaceConflict','message':json.dumps(conflicts,ensure_ascii=False)})
            destination=Path(goal.workspace_root)
            # Deepest removals first; parent directories before files on copy.
            for name in sorted(changed,key=lambda x:len(Path(x).parts),reverse=True):
                target=destination/name
                if name not in after and (target.exists() or target.is_symlink()):
                    if target.is_dir() and not target.is_symlink():shutil.rmtree(target)
                    else:target.unlink()
            for name in sorted(changed,key=lambda x:len(Path(x).parts)):
                if name not in after:continue
                source,target=staged/name,destination/name
                kind=after[name].get('kind')
                if kind=='directory':target.mkdir(parents=True,exist_ok=True)
                elif kind=='file':
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
                else:
                    raise ValueError('Background publication rejects nonregular entries')
            item['published']=True
        result.action_type='cc_job_output'
        result.metadata.update(task_id=arguments['task_id'],job_exit_code=process.returncode,
                               isolated_snapshot=True)
        return result

    def foreground(self,goal,arguments):
        started=self.start(goal,arguments)
        identifier=json.loads(started.output)['task_id']
        process=self.items[identifier]['process']
        try:process.wait(timeout=arguments.get('auto_background_after',60))
        except subprocess.TimeoutExpired:return started
        return self.output(goal,{'task_id':identifier})

    def kill(self,identifier):
        item=self._item(identifier);process=item['process']
        if process.poll() is None:
            # Python's SIGINT raises through the existing run_shell cleanup,
            # which stops and drains the sandbox's complete process group.
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=10)
        return dict(task_id=identifier,status='stopped',exit_code=process.returncode)

    def close(self):
        rows=[self.kill(identifier) for identifier in self.items]
        if not (self.root/'CLEANUP.json').exists():
            _write_new(self.root/'CLEANUP.json',dict(jobs=rows,all_workers_stopped=all(
                item['process'].poll() is not None for item in self.items.values())))
        return rows


def worker(directory):
    path=Path(directory);request=json.loads((path/'REQUEST.json').read_text())
    goal=GoalState.create(request=request['request'],workspace_root=str(path/'workspace'),constraints=[])
    harness=configure_project_tools(ActionHarness())
    if not harness._bubblewrap:
        raise RuntimeError('Background Bash requires the same workspace sandbox as foreground Bash')
    definition=harness.definition('run_shell')
    props={**definition.argument_schema,'timeout':{'type':'number','exclusiveMinimum':0,'maximum':3600}}
    harness._definitions['run_shell']=replace(definition,argument_schema=props)
    # This worker alone installs a streaming transport around the unchanged
    # sandbox command runner. No global Popen patch leaks into the parent run.
    from types import SimpleNamespace
    from . import harness as harness_module
    original_popen=subprocess.Popen

    class StreamingProcess:
        def __init__(self,*args,**kwargs):
            self.process=original_popen(*args,**kwargs)
            self.buffers=[bytearray(),bytearray()];self.readers=[];self.writer=None
            for index,(stream,name) in enumerate(((self.process.stdout,'LIVE_STDOUT.bin'),(self.process.stderr,'LIVE_STDERR.bin'))):
                if stream is None:continue
                def read(stream=stream,index=index,name=name):
                    with (path/name).open('ab',buffering=0) as destination:
                        while True:
                            data=os.read(stream.fileno(),65536)
                            if not data:break
                            self.buffers[index].extend(data);destination.write(data)
                thread=threading.Thread(target=read,daemon=True);thread.start();self.readers.append(thread)

        def __getattr__(self,name):return getattr(self.process,name)
        def __enter__(self):return self
        def __exit__(self,*args):return self.process.__exit__(*args)

        def communicate(self,input=None,timeout=None):
            if self.writer is None and self.process.stdin is not None:
                def write():
                    try:
                        if input:self.process.stdin.write(input);self.process.stdin.flush()
                    except (BrokenPipeError,OSError):pass
                    finally:self.process.stdin.close()
                self.writer=threading.Thread(target=write,daemon=True);self.writer.start()
            self.process.wait(timeout=timeout)
            for thread in self.readers:
                thread.join(timeout=5)
                if thread.is_alive():raise subprocess.TimeoutExpired(self.process.args,timeout)
            return tuple(bytes(value).decode('utf-8',errors='replace') for value in self.buffers)

    harness_module.subprocess=SimpleNamespace(**{**subprocess.__dict__,'Popen':StreamingProcess})
    try:
        result=harness.execute(TaskAction('run_shell',request['arguments']),goal)
    except BaseException as error:
        result=ActionResult('run_shell',False,error={'type':type(error).__name__,'message':str(error)})
    _write_new(path/'RESULT.json',result.to_dict())


if __name__=='__main__':
    worker(sys.argv[1])
