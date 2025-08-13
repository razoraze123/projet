from __future__ import annotations
from pathlib import Path
from typing import Iterable


def write_lines_txt(path: str | Path, lines: Iterable[str]) -> str:
    """
    Écrit des lignes texte en UTF-8, avec des retours Windows (CRLF)
    pour une compat Notepad parfaite. Ajoute un retour final.
    Retourne le chemin normalisé.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # IMPORTANT:
    # - ne PAS fixer newline="\n" (forcerait LF)
    # - laisser le default (newline=None) pour traduire '\n' -> CRLF sous Windows
    cleaned: list[str] = []
    seen: set[str] = set()
    for s in lines:
        s = (s or "").strip()
        if not s:
            continue
        if not s.startswith("http"):
            # on ignore ce qui n’est pas un lien absolu
            continue
        if s not in seen:
            seen.add(s)
            cleaned.append(s)

    with p.open("w", encoding="utf-8") as f:  # newline par défaut => CRLF sous Windows
        f.write("\n".join(cleaned))
        f.write("\n")  # s’assurer d’une dernière ligne

    return str(p)
