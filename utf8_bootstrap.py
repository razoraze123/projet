import os, sys, io

def _reconfig_stream(stream_name: str):
    s = getattr(sys, stream_name, None)
    if not s:
        return
    try:
        # Python 3.7+: reconfigure si dispo
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
            return
    except Exception:
        pass
    # Fallback: ré-enrouler le buffer (si possible)
    try:
        if hasattr(s, "buffer"):
            wrapped = io.TextIOWrapper(s.buffer, encoding="utf-8", errors="replace")
            setattr(sys, stream_name, wrapped)
    except Exception:
        pass

def _set_console_cp_utf8_on_windows():
    # Optionnel: bascule code page de la console Windows en UTF-8 (si console présente)
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass

def force_utf8_stdio():
    # Variables d'env pour les sous-processus Python
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    # Console Windows si présente
    _set_console_cp_utf8_on_windows()

    # Reconfig streams du process courant (si existent)
    _reconfig_stream("stdout")
    _reconfig_stream("stderr")
