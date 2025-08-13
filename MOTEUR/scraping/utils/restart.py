from __future__ import annotations
import os
import sys
import subprocess
import time
from log_safe import print_safe

def _build_relaunch_argv() -> list[str]:
    py = sys.executable or "python"
    # Cas PyInstaller / frozen
    if getattr(sys, "frozen", False):
        return [py] + sys.argv[1:]
    # Script direct
    script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if script and script.lower().endswith((".py", ".pyw")):
        return [py, script] + sys.argv[1:]
    # Fallback (ex: python -m package)
    return [py] + sys.argv[1:]

def relaunch_current_process(delay_sec: float = 0.25, *, cwd: str | None = None) -> None:
    argv = _build_relaunch_argv()
    try:
        print_safe(f"[restart] sys.executable = {sys.executable}")
        print_safe(f"[restart] sys.argv       = {sys.argv}")
        print_safe(f"[restart] relaunch argv  = {argv}")
        if cwd is None:
            cwd = os.getcwd()
        print_safe(f"[restart] cwd            = {cwd}")

        popen_kwargs = dict(
            cwd=cwd,
            close_fds=(os.name != "nt"),
            start_new_session=(os.name != "nt"),
        )
        if os.name == "nt":
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008
            popen_kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(argv, **popen_kwargs)
    except Exception as e:
        print_safe(f"[restart] Erreur au relancement: {e}")
    time.sleep(delay_sec)
