from PySide6.QtCore import QEvent, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QWidget


COLOR_LAMP_ALARM = QColor("#ff2d2d")
COLOR_LAMP_WARN = QColor("#ffcc33")
COLOR_LAMP_OFF = QColor("#182418")
COLOR_LAMP_DARK = QColor("#2a1410")
COLOR_LAMP_RING = QColor("#5a1a1a")
COLOR_LAMP_RING_OFF = QColor("#243024")
COLOR_LAMP_CAPTION = QColor("#8fb48f")


class AlarmLamp(QWidget):
    def __init__(self, caption, parent=None):
        super().__init__(parent)
        self._caption = caption
        self._level = 0
        self._on = True
        self._timer = QTimer(self)
        self._timer.setInterval(420)
        self._timer.timeout.connect(self._blink)
        self.setFixedSize(94, 74)

    def level(self):
        return self._level

    def set_level(self, level):
        level = int(level)
        if level == self._level:
            return
        self._level = level
        if level >= 2:
            self._on = True
            self._timer.start()
        else:
            self._timer.stop()
            self._on = True
        self.update()

    def _blink(self):
        self._on = not self._on
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 15
        cx = self.width() // 2
        cy = 24
        if self._level >= 2:
            color = COLOR_LAMP_ALARM
        elif self._level == 1:
            color = COLOR_LAMP_WARN
        else:
            color = COLOR_LAMP_OFF
        lit = self._level > 0 and self._on
        if lit:
            glow = QColor(color)
            glow.setAlpha(85)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPoint(cx, cy), radius + 7, radius + 7)
        if lit:
            body = color
        elif self._level:
            body = COLOR_LAMP_DARK
        else:
            body = COLOR_LAMP_OFF
        painter.setPen(QPen(COLOR_LAMP_RING if self._level else COLOR_LAMP_RING_OFF, 2))
        painter.setBrush(body)
        painter.drawEllipse(QPoint(cx, cy), radius, radius)
        font = painter.font()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffd8d8") if lit else COLOR_LAMP_CAPTION)
        painter.drawText(
            QRect(0, cy + radius + 5, self.width(), 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self._caption,
        )


class ScreenPulse(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active = False
        self._on = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._toggle)
        self.setGeometry(parent.rect())
        parent.installEventFilter(self)
        self._apply()

    def set_active(self, active):
        active = bool(active)
        if active == self._active:
            return
        self._active = active
        if active:
            self._on = True
            self._timer.start()
        else:
            self._timer.stop()
            self._on = False
        self._apply()

    def _toggle(self):
        self._on = not self._on
        self._apply()

    def _apply(self):
        if self._active and self._on:
            border = "4px solid rgba(255, 45, 45, 235)"
        elif self._active:
            border = "4px solid rgba(150, 20, 20, 120)"
        else:
            border = "4px solid rgba(255, 45, 45, 0)"
        self.setStyleSheet(
            "background: transparent; border: %s; border-radius: 6px;" % border
        )
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
        return False
