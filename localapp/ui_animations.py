# -*- coding: utf-8 -*-
from __future__ import annotations
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QPoint, QTimer, Qt
from PySide6.QtWidgets import QWidget, QStackedWidget, QLabel
from PySide6.QtGui import QGraphicsOpacityEffect


def fade_in(w: QWidget, msec=180):
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", w)
    anim.setDuration(msec)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class AnimatedStack(QStackedWidget):
    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex():
            return super().setCurrentIndex(index)
        old = self.currentWidget()
        super().setCurrentIndex(index)
        new = self.currentWidget()
        if not new:
            return
        eff = QGraphicsOpacityEffect(new)
        new.setGraphicsEffect(eff)
        fade = QPropertyAnimation(eff, b"opacity", self)
        fade.setDuration(180)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        pos = QPropertyAnimation(new, b"pos", self)
        pos.setDuration(180)
        pos.setStartValue(new.pos() + QPoint(0, 10))
        pos.setEndValue(new.pos())
        pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        grp = QParallelAnimationGroup(self)
        grp.addAnimation(fade)
        grp.addAnimation(pos)
        grp.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class Toast(QWidget):
    def __init__(self, parent=None, text="", kind="info"):
        super().__init__(parent, flags=Qt.ToolTip | Qt.FramelessWindowHint)
        self.setObjectName("Toast")
        self.lbl = QLabel(text, self)
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet(
            """
            QLabel{padding:8px 12px; border-radius:10px;
            background: rgba(26, 32, 44, .92); color: #fff; font-weight:600;}
            """
        )
        self.lbl.adjustSize()
        self.resize(self.lbl.size())
        QTimer.singleShot(2400, self.close)
        fade_in(self, 160)


def toast(parent: QWidget, text: str, kind="info"):
    if not parent:
        return
    t = Toast(parent, text, kind)
    g = parent.geometry()
    t.adjustSize()
    t.move(g.center().x() - t.width() // 2, g.bottom() - t.height() - 40)
    t.show()
