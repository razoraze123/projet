from __future__ import annotations
import os
import sys
import subprocess
import time


def relaunch_current_process(delay_sec: float = 0.2) -> None:
    """
    Relance ce programme avec les mêmes arguments, puis rend la main.
    Ne quitte PAS le process courant (laisse l'appelant le faire).
    """
    python = sys.executable
    script = os.path.abspath(sys.argv[0])
    argv = [python, script] + sys.argv[1:]
    try:
        creationflags = 0
        # Évite une console parasite sur Windows
        if os.name == "nt":
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008
            creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            argv,
            close_fds=(os.name != "nt"),
            creationflags=creationflags or 0
        )
    except Exception as e:
        print(f"[restart] Erreur au relancement: {e}")
    # petit délai pour laisser le temps à la nouvelle instance de démarrer
    time.sleep(delay_sec)
