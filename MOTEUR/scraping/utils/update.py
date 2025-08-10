from __future__ import annotations

import subprocess
from pathlib import Path

# Determine the project root (three levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def pull_latest(branch: str = "main") -> subprocess.CompletedProcess:
    """Pull the latest changes from the given branch.

    Parameters
    ----------
    branch:
        Name of the branch to pull from. Defaults to ``"main"``.

    Returns
    -------
    subprocess.CompletedProcess
        The result object from ``subprocess.run``.
    """
    return subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "pull", "origin", branch],
        capture_output=True,
        text=True,
    )
