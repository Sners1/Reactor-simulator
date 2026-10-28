import json
import os

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "saves", "tutorial.json"
)

CARD_WIDTH = 400

TUTORIAL_QSS = """
QFrame#tutorialCard {
    background-color: #0b0d0b;
    border: 2px solid #22ff77;
    border-radius: 6px;
}
QLabel#tutorialTitle {
    color: #9dff9d;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel#tutorialText {
    color: #b9e6b9;
    font-size: 13px;
}
QLabel#tutorialCounter {
    color: #5f7a5f;
    font-size: 11px;
    letter-spacing: 1px;
}
QPushButton#tutorialButton {
    background-color: #1f6f3f;
    color: #eaffea;
    border: 1px solid #22ff77;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
}
QPushButton#tutorialButton:hover {
    background-color: #2b8a4f;
}
QPushButton#tutorialSkip {
    background-color: transparent;
    color: #6d8a6d;
    border: none;
    padding: 4px 8px;
    font-size: 11px;
}
QPushButton#tutorialSkip:hover {
    color: #9dff9d;
}
"""


class _Highlight(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background: transparent; border: 2px dashed #22ff77; border-radius: 6px;"
        )
        self.hide()


class TutorialCard(QFrame):
    finished = Signal()

    def __init__(self, parent, steps):
        super().__init__(parent)
        self._steps = list(steps)
        self._index = -1
        self.setObjectName("tutorialCard")
        self.setStyleSheet(TUTORIAL_QSS)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(CARD_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        self._title = QLabel("")
        self._title.setObjectName("tutorialTitle")
        self._text = QLabel("")
        self._text.setObjectName("tutorialText")
        self._text.setWordWrap(True)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self._counter = QLabel("")
        self._counter.setObjectName("tutorialCounter")
        self._skip = QPushButton("ПРОПУСТИТЬ")
        self._skip.setObjectName("tutorialSkip")
        self._skip.clicked.connect(self.finish)
        self._button = QPushButton("ДАЛЕЕ")
        self._button.setObjectName("tutorialButton")
        self._button.clicked.connect(self.next_step)
        footer.addWidget(self._counter)
        footer.addStretch(1)
        footer.addWidget(self._skip)
        footer.addWidget(self._button)

        layout.addWidget(self._title)
        layout.addWidget(self._text)
        layout.addLayout(footer)

        self._highlight = _Highlight(parent)
        self.hide()
        parent.installEventFilter(self)

    def start(self):
        self._index = -1
        self.next_step()

    def next_step(self):
        self._index += 1
        if self._index >= len(self._steps):
            self.finish()
            return
        title, text, widget = self._steps[self._index]
        self._title.setText(title)
        self._text.setText(text)
        self._counter.setText("ШАГ %d ИЗ %d" % (self._index + 1, len(self._steps)))
        last = self._index == len(self._steps) - 1
        self._button.setText("ПОНЯТНО" if last else "ДАЛЕЕ")
        self._skip.setVisible(not last)
        self._text.setMinimumHeight(0)
        self.adjustSize()
        self._place(widget)
        self.show()
        self.raise_()

    def finish(self):
        self._highlight.hide()
        self.hide()
        self.finished.emit()

    def _place(self, widget):
        parent = self.parentWidget()
        if parent is None:
            return
        if widget is None or not widget.isVisible():
            self._highlight.hide()
            size = self.sizeHint()
            self.setGeometry(
                parent.width() - size.width() - 16,
                parent.height() - size.height() - 16,
                size.width(),
                size.height(),
            )
            return
        rect = QRect(widget.mapTo(parent, QPoint(0, 0)), widget.size())
        self._highlight.setGeometry(rect.adjusted(-6, -6, 6, 6))
        self._highlight.show()
        self._highlight.raise_()

        size = self.sizeHint()
        x = rect.center().x() - size.width() // 2
        y = rect.bottom() + 12
        if y + size.height() > parent.height() - 8:
            y = rect.top() - size.height() - 12
        x = max(8, min(x, parent.width() - size.width() - 8))
        y = max(8, min(y, parent.height() - size.height() - 8))
        self.setGeometry(x, y, size.width(), size.height())
        self._highlight.raise_()
        self.raise_()

    def eventFilter(self, obj, event):
        if (
            obj is self.parentWidget()
            and event.type() == QEvent.Type.Resize
            and self.isVisible()
        ):
            if 0 <= self._index < len(self._steps):
                self._place(self._steps[self._index][2])
        return False


def tutorial_seen(path=STATE_FILE):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return False
    return bool(isinstance(data, dict) and data.get("seen"))


def mark_tutorial_seen(path=STATE_FILE):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"seen": True}, handle)
    except OSError:
        pass
