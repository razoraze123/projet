from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    profiles_changed = Signal()
    history_changed = Signal()


# singleton
bus = EventBus()
