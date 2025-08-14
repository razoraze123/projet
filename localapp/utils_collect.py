# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, time
from pathlib import Path
from typing import Iterable, List

ALLOWED_EXTS = {
    ".py", ".pyi", ".txt", ".md", ".json", ".yaml", ".yml", ".ini", ".cfg",
    ".qss", ".qrc", ".html", ".htm", ".css", ".js", ".ts", ".tsx", ".svg"
}
IGNORE_DIRS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
               "venv", ".venv", "env", "node_modules", "build", "dist", ".tox", ".ruff_cache"}
MAX_BYTES = 1_000_000  # 1 Mo

def detect_project_root(start: Path | None = None) -> Path:
    """Essaie ../ (repo) puis répertoire courant du fichier appelant."""
    if start is None:
        start = Path(__file__).resolve()
    # remonte jusqu'à trouver .git ou requirements/pyproject
    cur = start
    for _ in range(6):
        p = cur.parent
        if (p / '.git').exists() or (p / 'requirements.txt').exists() or (p / 'pyproject.toml').exists():
            return p
        cur = p
    # fallback: deux niveaux au-dessus de /localapp/
    return Path(__file__).resolve().parents[1]

def iter_sources(root: Path, *, out_path: Path | None = None) -> Iterable[Path]:
    """Parcourt root en ignorant dossiers poubelles; garde extensions whitelistées, < MAX_BYTES, et exclut out_path."""
    for dirpath, dirnames, filenames in os.walk(root):
        # prune des dossiers ignorés
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            # exclure copy.txt lui-même
            if out_path and p.resolve() == out_path.resolve():
                continue
            ext = p.suffix.lower()
            if ext not in ALLOWED_EXTS:
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
            except Exception:
                continue
            yield p

def build_copy_txt(root: Path, out_path: Path) -> dict:
    """Construit copy.txt; renvoie stats."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    files: List[Path] = list(iter_sources(root, out_path=out_path))
    files.sort(key=lambda x: x.as_posix())

    written_bytes = 0
    written_files = 0
    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    with open(out_path, "w", encoding="utf-8", errors="replace") as out:
        out.write("# copy.txt regénéré automatiquement\n")
        out.write(f"# {now}\n\n")
        for fp in files:
            rel = fp.relative_to(root)
            try:
                txt = fp.read_text(encoding="utf-8", errors="replace")
            except Exception as ex:
                # si lecture impossible, on note et on continue
                out.write(f"### >>> {rel} (lecture impossible: {ex})\n\n")
                continue
            lines = txt.count("\n") + (1 if txt and not txt.endswith("\n") else 0)
            header = f"### >>> {rel} ({lines} lignes)\n"
            out.write(header)
            out.write(txt)
            if not txt.endswith("\n"):
                out.write("\n")
            out.write("\n")
            written_files += 1
            written_bytes += len(header.encode("utf-8")) + len(txt.encode("utf-8")) + 1
    return {"files": written_files, "bytes": written_bytes, "out": str(out_path)}
