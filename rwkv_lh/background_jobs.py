"""Background shell jobs that outlive one tool call.

A blocking-only shell cannot deliver a web project: the call that starts a dev
server is the call that was supposed to check it. These jobs exist so the model
can start a server, observe it and stop it across separate calls.

Three facts shape the design, and each one is a way an earlier round fooled
itself:

* A job is observed, never promised. `running` is what a waitpid said a moment
  ago. A log line reading "ready" is evidence the process once printed it, not
  that the process is up now, so nothing here reports liveness as a guarantee.
* Pipes must drain continuously. `communicate()` cannot be used, because a
  caller that stops reading fills the 64 KiB pipe buffer and silently wedges the
  child. Reader threads append to on-disk logs so the child never blocks.
* A PID is not an identity. PIDs are recycled, and a project can resume in a new
  host process where the Popen object is gone. Every job records its start ticks
  and argv digest, and a mismatch is reported as an unknown outcome rather than
  acted upon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from uuid import uuid4

JOB_PROTOCOL = 'rwkv-lh.coder.background-job.v1'
CLEANUP_GRACE_SECONDS = 5.0


def process_start_ticks(pid):
    """Start time in clock ticks since boot, used to tell a reused PID apart."""
    try:
        fields = Path('/proc', str(pid), 'stat').read_bytes()
    except (OSError, ValueError):
        return None
    # The comm field may contain spaces and parentheses; fields after the last
    # ')' are positional, and starttime is the 22nd overall.
    tail = fields[fields.rfind(b')') + 1:].split()
    return int(tail[19]) if len(tail) > 19 else None


@dataclass
class BackgroundJob:
    handle: str
    argv: list
    cwd: str
    pid: int
    start_ticks: int | None
    stdout_path: Path
    stderr_path: Path
    process: subprocess.Popen | None = None
    readers: tuple = ()
    cursors: dict = field(default_factory=lambda: {'stdout': 0, 'stderr': 0})
    exit_code: int | None = None
    reaped: bool = False
    # The sandbox PID-namespace init, when bwrap reported one. Killing it makes
    # the kernel tear down every process in the namespace.
    namespace_pid: int | None = None

    @property
    def argv_digest(self):
        return hashlib.sha256(json.dumps(self.argv, ensure_ascii=False).encode()).hexdigest()

    def identity(self):
        return {'protocol': JOB_PROTOCOL, 'handle': self.handle, 'pid': self.pid,
                'start_ticks': self.start_ticks, 'argv_digest': self.argv_digest,
                'cwd': self.cwd, 'stdout_path': str(self.stdout_path),
                'stderr_path': str(self.stderr_path)}

    def identity_matches(self):
        """Whether this PID is still the process we started.

        Owning the Popen settles it: until we reap the child it stays a zombie
        holding its PID, so the PID cannot have been recycled, and once we have
        reaped it we observed its exit directly. The /proc comparison is for the
        other case only -- a project resumed in a new host process, where the
        Popen is gone and a live PID may belong to someone else entirely.
        """
        if self.process is not None or self.reaped:
            return True
        if self.start_ticks is None:
            return None
        return process_start_ticks(self.pid) == self.start_ticks


class JobTable:
    """Owns live jobs for one project and the log files they append to."""

    def __init__(self, directory):
        # Handles restart at job-1 for every table, so a shared parent directory
        # would let one project read another's stale log. The per-table segment
        # keeps each project's job output its own.
        self.directory = Path(directory) / uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        self.jobs = {}
        self._sequence = 0

    def _next_handle(self):
        self._sequence += 1
        return 'job-%d' % self._sequence

    @staticmethod
    def _read_namespace_pid(info_read, timeout=5.0):
        """Read bwrap's reported child-pid, or None when it never arrives."""
        try:
            deadline = time.monotonic() + timeout
            os.set_blocking(info_read, False)
            raw = b''
            while time.monotonic() < deadline:
                try:
                    chunk = os.read(info_read, 65536)
                except BlockingIOError:
                    time.sleep(0.02)
                    continue
                if not chunk:
                    break
                raw += chunk
                if b'\n\n' in raw or raw.rstrip().endswith(b'}'):
                    break
            if not raw:
                return None  # bwrap failed before creating the namespace
            return int(json.loads(raw.decode('utf-8').split('\n\n')[0])['child-pid'])
        except (OSError, ValueError, KeyError):
            return None
        finally:
            os.close(info_read)

    def _drain(self, stream, path):
        """Append to the log until EOF so the child is never blocked on a pipe.

        read1() performs a single underlying read and returns whatever is
        available. Plain read(n) would block until n bytes or EOF, which would
        hold a dev server's startup banner in the pipe until the process ended
        -- the opposite of what an incremental reader is for.
        """
        def pump():
            with open(path, 'ab', buffering=0) as sink:
                for chunk in iter(lambda: stream.read1(65536), b''):
                    sink.write(chunk)
            stream.close()
        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        return thread

    def start(self, argv, *, cwd, env, stdin='', sandbox_info_fd=False):
        """Launch a job, learning its sandbox PID-namespace init when sandboxed.

        `--new-session` puts the sandboxed command in its own session, so
        killing the outer bwrap's process group does not reach it, and without
        `--die-with-parent` those processes survive as orphans. bwrap reports
        the namespace init's pid on `--info-fd`; killing that init makes the
        kernel kill and reap the whole namespace, which is the only reliable
        way to stop a background sandbox.
        """
        handle = self._next_handle()
        stdout_path = self.directory / (handle + '.stdout')
        stderr_path = self.directory / (handle + '.stderr')
        stdout_path.touch()
        stderr_path.touch()
        info_read = info_write = None
        if sandbox_info_fd:
            info_read, info_write = os.pipe()
            argv = [argv[0], '--info-fd', str(info_write), *argv[1:]]
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, shell=False,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True,
                                       pass_fds=(info_write,) if info_write is not None else ())
        finally:
            if info_write is not None:
                os.close(info_write)
        namespace_pid = self._read_namespace_pid(info_read) if info_read is not None else None
        if process.stdin is not None:
            try:
                process.stdin.write(stdin.encode('utf-8'))
            finally:
                process.stdin.close()
        job = BackgroundJob(handle=handle, argv=list(argv), cwd=str(cwd), pid=process.pid,
                            start_ticks=process_start_ticks(process.pid),
                            stdout_path=stdout_path, stderr_path=stderr_path, process=process,
                            namespace_pid=namespace_pid)
        job.readers = (self._drain(process.stdout, stdout_path),
                       self._drain(process.stderr, stderr_path))
        self.jobs[handle] = job
        return job

    def get(self, handle):
        job = self.jobs.get(handle)
        if job is None:
            raise KeyError(handle)
        return job

    def poll(self, job):
        """Record an exit observed since the last check; never block."""
        if job.process is not None and job.exit_code is None:
            code = job.process.poll()
            if code is not None:
                job.exit_code = code
                job.reaped = True
        return job.exit_code

    def read(self, job, *, max_bytes=65536):
        """Return output appended since the previous read of this job."""
        self.poll(job)
        chunks = {}
        for name, path in (('stdout', job.stdout_path), ('stderr', job.stderr_path)):
            with open(path, 'rb') as source:
                source.seek(job.cursors[name])
                data = source.read(max_bytes)
                job.cursors[name] += len(data)
            chunks[name] = data.decode('utf-8', 'replace')
        total = os.path.getsize(job.stdout_path) + os.path.getsize(job.stderr_path)
        consumed = job.cursors['stdout'] + job.cursors['stderr']
        return {'stdout': chunks['stdout'], 'stderr': chunks['stderr'],
                'running': job.exit_code is None, 'exit_code': job.exit_code,
                'unread_bytes': max(0, total - consumed)}

    def _gone(self, job):
        """Whether the job is actually finished, judged by the sandbox init.

        For a sandboxed job the namespace init is authoritative: while it lives
        the namespace still holds processes, whatever the outer bwrap did.
        """
        self.poll(job)
        if job.namespace_pid is not None:
            try:
                os.kill(job.namespace_pid, 0)
                return False
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
        return job.exit_code is not None

    @staticmethod
    def _signal(job, number):
        """Signal the sandbox namespace init first, then the outer group.

        The namespace init is what tears the sandbox down; the outer group
        alone cannot reach a command that `--new-session` moved elsewhere.
        """
        if job.namespace_pid is not None:
            try:
                os.kill(job.namespace_pid, number)
            except (ProcessLookupError, PermissionError):
                pass
        try:
            os.killpg(job.pid, number)
        except ProcessLookupError:
            pass

    def stop(self, job, *, grace=CLEANUP_GRACE_SECONDS):
        """Terminate the job's process group and report what was observed.

        A job that already exited is reported as such, not as a failure. When
        the group cannot be confirmed gone the caller must keep the operation
        pending instead of claiming success.
        """
        from .harness import UncertainToolOutcome
        already = self.poll(job) is not None
        matched = job.identity_matches()
        if matched is False:
            self.jobs.pop(job.handle, None)
            return {'handle': job.handle, 'already_exited': already,
                    'exit_code': job.exit_code, 'identity_verified': False,
                    'outcome': 'unknown_process_identity'}
        if not already:
            self._signal(job, signal.SIGTERM)
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline and not self._gone(job):
                time.sleep(0.05)
        # The outer bwrap exiting proves nothing: the kernel ignores a SIGTERM
        # that a PID-namespace init has no handler for, so the sandbox can
        # still be serving. SIGKILL cannot be ignored even by that init, and
        # killing it makes the kernel tear down the namespace.
        if not self._gone(job):
            self._signal(job, signal.SIGKILL)
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline and not self._gone(job):
                time.sleep(0.05)
            if not self._gone(job):
                raise UncertainToolOutcome(
                    'background job sandbox did not exit; preserve pending operation')
        if job.process is not None and job.exit_code is None:
            # Reap our own child so it does not linger as a zombie.
            try:
                job.process.wait(timeout=grace)
                job.exit_code = job.process.returncode
                job.reaped = True
            except subprocess.TimeoutExpired as exc:
                raise UncertainToolOutcome(
                    'background job cleanup did not finish; preserve pending operation') from exc
        for reader in job.readers:
            reader.join(timeout=grace)
        self.jobs.pop(job.handle, None)
        return {'handle': job.handle, 'already_exited': already, 'exit_code': job.exit_code,
                'identity_verified': matched is not False, 'outcome': 'stopped'}

    def stop_all(self):
        """Reclaim every job; an uncertain cleanup propagates, it is not hidden."""
        return [self.stop(job) for job in list(self.jobs.values())]
