"""Launch one release-gate command in an isolated, signal-correct process group."""

from __future__ import annotations

import os
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
        received_signals: list[int] = []

        def record_signal(signum: int, _frame: object) -> None:
            received_signals.append(signum)

        for managed_signal in managed_signals:
            signal.signal(managed_signal, record_signal)
        command_pid = os.fork()
        if command_pid == 0:
            for managed_signal in managed_signals:
                signal.signal(managed_signal, signal.SIG_DFL)
            try:
                os.execvp(
                    "sh",
                    [
                        "sh",
                        "-c",
                        'trap - HUP INT QUIT TERM; "$@"; status=$?; exit "$status"',
                        "process-group-launcher",
                        *sys.argv[1:],
                    ],
                )
            except OSError:
                try:
                    os.write(write_fd, b"!")
                finally:
                    os._exit(127)
        while True:
            try:
                _, status = os.waitpid(command_pid, 0)
                break
            except InterruptedError:
                continue
        if received_signals:
            os._exit(128 + received_signals[-1])
        if os.WIFEXITED(status):
            os._exit(os.WEXITSTATUS(status))
        os._exit(128 + os.WTERMSIG(status))

    os.close(write_fd)
    try:
        exec_failed = os.read(read_fd, 1)
    finally:
        os.close(read_fd)
    finished_pid, status = os.waitpid(child_pid, os.WNOHANG)
    if exec_failed or (finished_pid == child_pid and not os.WIFEXITED(status)):
        if finished_pid != child_pid:
            _, status = os.waitpid(child_pid, 0)
        if ready_path:
            try:
                os.unlink(ready_path)
            except FileNotFoundError:
                pass
        raise SystemExit(127)
    if ready_path:
        with open(ready_path, "x", encoding="utf-8"):
            pass
    if finished_pid != child_pid:
        _, status = os.waitpid(child_pid, 0)
    if os.WIFEXITED(status):
        raise SystemExit(os.WEXITSTATUS(status))
    raise SystemExit(128 + os.WTERMSIG(status))


if __name__ == "__main__":
    main()
