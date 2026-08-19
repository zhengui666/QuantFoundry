"""Launch one release-gate command in an isolated, signal-correct process group."""

from __future__ import annotations

import os
import signal
import sys
import threading


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: process_group_launcher.py COMMAND [ARG ...]")
    # POSIX shells start asynchronous commands with these signals ignored or
    # blocked. Those settings survive exec unless explicitly restored.
    managed_signals = (
        signal.SIGHUP,
        signal.SIGINT,
        signal.SIGQUIT,
        signal.SIGTERM,
    )
    parent_received_signals: list[int] = []

    os.setsid()
    signal.pthread_sigmask(signal.SIG_BLOCK, managed_signals)
    for managed_signal in managed_signals:
        signal.signal(managed_signal, signal.SIG_DFL)
    ready_path = os.environ.get("QF_PROCESS_GROUP_READY")
    read_fd, write_fd = os.pipe()
    os.set_inheritable(write_fd, False)
    child_pid = os.fork()
    if child_pid == 0:
        os.close(read_fd)
        for managed_signal in managed_signals:
            signal.signal(managed_signal, signal.SIG_DFL)
        signal.pthread_sigmask(signal.SIG_BLOCK, managed_signals)
        command_pid = os.fork()
        if command_pid == 0:
            for managed_signal in managed_signals:
                signal.signal(managed_signal, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK, managed_signals)
            try:
                os.execvp(
                    "sh",
                    [
                        "sh",
                        "-c",
                        "trap 'exit 129' HUP; trap 'exit 130' INT; trap 'exit 131' QUIT; trap 'exit 143' TERM; \"$@\"; status=$?; exit \"$status\"",
                        "process-group-launcher",
                        *sys.argv[1:],
                    ],
                )
            except OSError:
                try:
                    os.write(write_fd, b"!")
                finally:
                    os._exit(127)
        os.close(write_fd)
        while True:
            try:
                _, status = os.waitpid(command_pid, 0)
                break
            except InterruptedError:
                continue
        if os.WIFEXITED(status):
            os._exit(os.WEXITSTATUS(status))
        os._exit(128 + os.WTERMSIG(status))

    os.close(write_fd)
    parent_signal_received = threading.Event()

    def wait_for_parent_signal() -> None:
        parent_received_signals.append(signal.sigwait(managed_signals))
        parent_signal_received.set()

    threading.Thread(target=wait_for_parent_signal, daemon=True).start()
    try:
        while True:
            try:
                exec_failed = os.read(read_fd, 1)
                break
            except InterruptedError:
                continue
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
        while True:
            try:
                _, status = os.waitpid(child_pid, 0)
                break
            except InterruptedError:
                continue
    parent_signal_received.wait(0.25)
    if parent_received_signals:
        raise SystemExit(128 + parent_received_signals[-1])
    if os.WIFEXITED(status):
        raise SystemExit(os.WEXITSTATUS(status))
    raise SystemExit(128 + os.WTERMSIG(status))


if __name__ == "__main__":
    main()
