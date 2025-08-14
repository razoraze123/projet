# -*- coding: utf-8 -*-
from __future__ import annotations
from PySide6.QtGui import QIcon


def qicon(name: str) -> QIcon:
    return QIcon(f":/icons/{name}.svg")
