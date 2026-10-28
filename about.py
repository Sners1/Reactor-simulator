"""Экран «О билде» — информация о сборке и контакты для баг-репортов."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from menu import MENU_QSS, _header_frame


ABOUT_QSS = MENU_QSS + """
QTextBrowser#aboutBody {
    background-color: #0d100d;
    border: 1px solid #2c4a2c;
    border-radius: 6px;
    color: #c9f5c9;
    font-size: 13px;
    padding: 20px;
}
"""


ABOUT_HTML = """<body style='font-family: Consolas, monospace;'>
<h2 style='color:#9dff9d; letter-spacing:3px; margin-bottom:4px;'>BETA BUILD</h2>
<p style='color:#6d8a6d; margin-top:0;'>Сборка: Beta build by Sners1</p>
<p style='color:#ff2d2d; font-weight:bold;'>ВНИМАНИЕ: это бета-версия. Возможны баги, дюпы и ошибки баланса.</p>
<p style='color:#ffcc44; font-weight:bold;'>Со всеми багами, дюпами, несостыковками или же лже-информацией - писать @Sners1 , в телеграм</p>
<p>О всех багах, дюпах и ошибках пишите:</p>
<ul>
  <li><b>Telegram:</b> <a href='https://t.me/Sners1' style='color:#7dff9a;'>https://t.me/Sners1</a></li>
  <li><b>Telegram:</b> <a href='https://t.me/Sners1' style='color:#7dff9a;'>@Sners1</a></li>
</ul>
<p style='color:#6d8a6d;'>В сообщении укажите версию, описание шагов и, если можно, скриншот. Спасибо за помощь в тестировании!</p>
<p style='color:#4d634d;'>© 2026 Sners1</p>
</body>"""


class AboutWindow(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("РЕАКТОР — о билде")
        self.resize(900, 640)
        self.setStyleSheet(ABOUT_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(_header_frame("О БИЛДЕ", "BETA BUILD BY SNERS1"))

        body = QTextBrowser()
        body.setObjectName("aboutBody")
        body.setOpenExternalLinks(True)
        body.setHtml(ABOUT_HTML)
        root.addWidget(body, 1)

        back = QPushButton("НАЗАД")
        back.setObjectName("menuButtonSmall")
        back.clicked.connect(self.back_requested.emit)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(back)
        holder = QWidget()
        holder.setLayout(row)
        root.addWidget(holder)

        mark = QLabel('@Sners1')
        mark.setAlignment(Qt.AlignmentFlag.AlignRight)
        mark.setStyleSheet('color: rgba(170, 140, 255, 90); font-size: 10px; letter-spacing: 1px;')
        root.addWidget(mark)
