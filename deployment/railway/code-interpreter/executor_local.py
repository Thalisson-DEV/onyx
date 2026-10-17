"""Run the Python snippet as a child process of this container.

Railway has no Docker socket and no privileged containers, so neither the
docker nor the kubernetes backend can start a sandbox there. This backend runs
each execution in a fresh temporary workspace, as an unprivileged user, with a
CPU limit and a wall-clock timeout. The isolation is the service container
itself: it holds no credentials and talks only to the API server.
"""

from __future__ import annotations

import os
import pwd
import resource
import shutil
import subprocess
import tempfile
import time
from collections.abc import Generator, Sequence
from pathlib import Path, PurePosixPath

from app.services.executor_base import (
    BaseExecutor,
    EntryKind,
    ExecutionResult,
    HealthCheck,
    StreamEvent,
    StreamResult,
    WorkspaceEntry,
    wrap_last_line_interactive,
)
from app.services.executor_docker import _stream_process_output, _write_stdin

PYTHON = os.environ.get("LOCAL_EXECUTOR_PYTHON") or "/opt/executor-venv/bin/python"
RUN_AS = os.environ.get("LOCAL_EXECUTOR_USER") or "nobody"
ENTRYPOINT = "__main__.py"


def _relative(path: str) -> PurePosixPath:
    clean = PurePosixPath(path)
    if clean.is_absolute() or ".." in clean.parts or not clean.parts:
        raise ValueError(f"Invalid workspace path: {path}")
    return clean


class LocalExecutor(BaseExecutor):
    def __init__(self) -> None:
        user = pwd.getpwnam(RUN_AS)
        self.uid = user.pw_uid
        self.gid = user.pw_gid

    def check_health(self) -> HealthCheck:
        if not Path(PYTHON).exists():
            return HealthCheck(status="error", message=f"{PYTHON} not found")
        return HealthCheck(status="ok")

    def _workspace(
        self,
        code: str,
        files: Sequence[tuple[str, bytes]] | None,
        last_line_interactive: bool,
    ) -> Path:
        root = Path(tempfile.mkdtemp(prefix="code-exec-"))
        for name, content in files or ():
            target = root / _relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        source = wrap_last_line_interactive(code) if last_line_interactive else code
        (root / ENTRYPOINT).write_text(source, encoding="utf-8")
        for path in [root, *root.rglob("*")]:
            os.chown(path, self.uid, self.gid)
        return root

    def _start(
        self,
        root: Path,
        cpu_time_limit_sec: int | None,
    ) -> subprocess.Popen[bytes]:
        uid, gid = self.uid, self.gid

        def drop() -> None:
            os.setsid()
            if cpu_time_limit_sec:
                resource.setrlimit(
                    resource.RLIMIT_CPU, (cpu_time_limit_sec, cpu_time_limit_sec)
                )
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)

        env = {
            "PATH": f"{Path(PYTHON).parent}:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(root),
            "LANG": "C.UTF-8",
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(root / ".matplotlib"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        return subprocess.Popen(
            [PYTHON, ENTRYPOINT],
            cwd=root,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=drop,  # noqa: PLW1509 - single-threaded setup before exec
        )

    @staticmethod
    def _kill(proc: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(proc.pid, 9)
        except ProcessLookupError:
            pass
        proc.kill()

    @staticmethod
    def _snapshot(root: Path) -> tuple[WorkspaceEntry, ...]:
        entries: list[WorkspaceEntry] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if relative == ENTRYPOINT or relative.startswith(".matplotlib"):
                continue
            if path.is_dir():
                entries.append(WorkspaceEntry(path=relative, kind=EntryKind.DIRECTORY))
            elif path.is_file():
                entries.append(
                    WorkspaceEntry(
                        path=relative, kind=EntryKind.FILE, content=path.read_bytes()
                    )
                )
        return tuple(entries)

    def execute_python(
        self,
        *,
        code: str,
        stdin: str | None,
        timeout_ms: int,
        max_output_bytes: int,
        cpu_time_limit_sec: int | None = None,
        memory_limit_mb: int | None = None,
        files: Sequence[tuple[str, bytes]] | None = None,
        last_line_interactive: bool = True,
    ) -> ExecutionResult:
        start = time.perf_counter()
        root = self._workspace(code, files, last_line_interactive)
        try:
            proc = self._start(root, cpu_time_limit_sec)
            try:
                stdout, stderr = proc.communicate(
                    input=stdin.encode("utf-8") if stdin is not None else None,
                    timeout=timeout_ms / 1000.0,
                )
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                self._kill(proc)
                stdout, stderr = proc.communicate()
            snapshot = self._snapshot(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        return ExecutionResult(
            stdout=self.truncate_output(stdout or b"", max_output_bytes),
            stderr=self.truncate_output(stderr or b"", max_output_bytes),
            exit_code=None if timed_out else proc.returncode,
            timed_out=timed_out,
            duration_ms=int((time.perf_counter() - start) * 1000),
            files=snapshot,
        )

    def execute_python_streaming(
        self,
        *,
        code: str,
        stdin: str | None,
        timeout_ms: int,
        max_output_bytes: int,
        cpu_time_limit_sec: int | None = None,
        memory_limit_mb: int | None = None,
        files: Sequence[tuple[str, bytes]] | None = None,
        last_line_interactive: bool = True,
    ) -> Generator[StreamEvent, None, None]:
        start = time.perf_counter()
        root = self._workspace(code, files, last_line_interactive)
        try:
            proc = self._start(root, cpu_time_limit_sec)
            _write_stdin(proc, stdin)
            deadline = time.monotonic() + timeout_ms / 1000.0
            timed_out = yield from _stream_process_output(proc, deadline, max_output_bytes)
            if timed_out:
                self._kill(proc)
            proc.wait()
            snapshot = self._snapshot(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        yield StreamResult(
            exit_code=None if timed_out else proc.returncode,
            timed_out=timed_out,
            duration_ms=int((time.perf_counter() - start) * 1000),
            files=snapshot,
        )
