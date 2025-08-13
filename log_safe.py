import sys
from typing import Any

def _safe_write(stream, text: str):
    # Écrit en gérant les caractères non encodables (remplacement)
    try:
        stream.write(text + "\n")
    except Exception:
        enc = getattr(stream, "encoding", None) or "utf-8"
        # backslashreplace évite les plantages même en cp1252
        stream.write(text.encode(enc, "backslashreplace").decode(enc) + "\n")

def print_safe(*args: Any, sep: str=" ", end: str="\n"):
    # Équivalent print, mais robuste à l'encodage
    out = getattr(sys, "stdout", None)
    if not out:
        return
    s = sep.join("" if a is None else str(a) for a in args)
    if end and not s.endswith(end):
        s = s + end
    try:
        out.write(s)
    except Exception:
        _safe_write(out, s.rstrip("\n"))

def open_utf8(path: str, mode: str="r"):
    # Ouvre un fichier texte en UTF-8 avec remplacement robuste
    if "b" in mode:
        return open(path, mode)  # binaire: inchangé
    return open(path, mode, encoding="utf-8", errors="replace")
