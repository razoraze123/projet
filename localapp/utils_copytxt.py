from pathlib import Path
import datetime

def regenerate_copy_txt(target_path: str) -> str:
    p = Path(target_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# copy.txt regénéré automatiquement",
        f"# {datetime.datetime.now().isoformat()}",
        ""
    ]
    p.write_text("\n".join(content), encoding="utf-8")
    return f"copy.txt régénéré : {p}"
