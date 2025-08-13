# -*- coding: utf-8 -*-
# localapp/utf8_bootstrap.py
import os, sys, io


def _reconfig_stream(stream_name: str):
    s = getattr(sys, stream_name, None)
    if not s:
        return
    try:
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
            return
    except Exception:
        pass
    try:
        if hasattr(s, "buffer"):
            wrapped = io.TextIOWrapper(s.buffer, encoding="utf-8", errors="replace")
            setattr(sys, stream_name, wrapped)
    except Exception:
        pass


def _set_console_cp_utf8_on_windows():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass


def force_utf8_stdio():
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _set_console_cp_utf8_on_windows()
    _reconfig_stream("stdout")
    _reconfig_stream("stderr")
