"""Launch one release-gate command in an isolated, signal-correct process group."""

from __future__ import annotations

import os
import select
import signal
import sys


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: process_group_launcher.py COMMAND [ARG ...]")
    # POSIX shells start asynchronous commands with SIGINT/SIGQUIT ignored.
    # Those dispositions survive exec unless explicitly restored.
    managed_signals = (
        signal.SIGHUP,
        signal.SIGINT,
        signal.SIGQUIT,
        signal.SIGTERM,
    )
    os.setsid()
    for managed_signal in managed_signals:
        signal.signal(managed_signal, signal.SIG_IGN)
    ready_path = os.environ.get("QF_PROCESS_GROUP_READY")
    read_fd, write_fd = os.pipe()
    os.set_inheritable(write_fd, False)
    child_pid = os.fork()
    if child_pid == 0:
        os.close(read_fd)
        for managed_signal in managed_signals:
            signal.signal(managed_signal, signal.SIG_DFL)
        try:
            os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
        except OSError:
            try:
                os.write(write_fd, b"!")
            finally:
                os._exit(127)

    watcher_pid = os.fork()
    if watcher_pid == 0:
        os.close(read_fd)
        os.close(write_fd)
        for managed_signal in managed_signals:
            signal.signal(managed_signal, signal.SIG_DFL)
        try:
            os.execvp("sleep", ["sleep", "2147483647"])
        except OSError:
            os._exit(127)

    os.close(write_fd)

    def remove_ready_path() -> None:
        if ready_path:
            try:
                os.unlink(ready_path)
            except FileNotFoundError:
                pass

    def stop_watcher() -> None:
        try:
            os.kill(watcher_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(watcher_pid, 0)
        except ChildProcessError:
            pass

    def abort_for_signal(signum: int) -> None:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(child_pid, 0)
        except ChildProcessError:
            pass
        remove_ready_path()
        raise SystemExit(128 + signum)

    def check_watcher() -> None:
        finished_pid, watcher_status = os.waitpid(watcher_pid, os.WNOHANG)
        if finished_pid != watcher_pid:
            return
        if os.WIFSIGNALED(watcher_status):
            signum = os.WTERMSIG(watcher_status)
            if signum in managed_signals:
                abort_for_signal(signum)
        raise SystemExit(127)

    while True:
        check_watcher()
        readable, _, _ = select.select([read_fd], [], [], 0.05)
        if readable:
            break
    try:
        exec_failed = os.read(read_fd, 1)
    finally:
        os.close(read_fd)
    finished_pid, status = os.waitpid(child_pid, os.WNOHANG)
    if exec_failed or (finished_pid == child_pid and not os.WIFEXITED(status)):
        if finished_pid != child_pid:
            _, status = os.waitpid(child_pid, 0)
        stop_watcher()
        remove_ready_path()
        raise SystemExit(127)
    if ready_path:
        with open(ready_path, "x", encoding="utf-8"):
            pass
    while finished_pid != child_pid:
        check_watcher()
        finished_pid, status = os.waitpid(child_pid, os.WNOHANG)
        if finished_pid != child_pid:
            select.select([], [], [], 0.05)
    stop_watcher()
    if os.WIFEXITED(status):
        raise SystemExit(os.WEXITSTATUS(status))
    raise SystemExit(128 + os.WTERMSIG(status))


if __name__ == "__main__":
    main()
