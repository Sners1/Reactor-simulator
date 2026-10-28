"""Экран «Руководство» — справочник оператора в трёх разделах."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from menu import MENU_QSS, _header_frame


GUIDE_QSS = MENU_QSS + """
QTabWidget::pane {
    border: 1px solid #2c4a2c;
    border-radius: 6px;
    background-color: #0d100d;
    top: -1px;
}
QTabBar::tab {
    background-color: #0b0e0b;
    color: #6d8a6d;
    border: 1px solid #24361f;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 10px 18px;
    margin-right: 3px;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
}
QTabBar::tab:selected {
    background-color: #16261a;
    color: #9dff9d;
    border-color: #3f6a3f;
}
QTabBar::tab:hover {
    color: #7dff9a;
}
QTableWidget {
    background-color: #0a0c0a;
    alternate-background-color: #0e130e;
    color: #c9f5c9;
    gridline-color: #24361f;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    selection-background-color: #1f3a24;
    selection-color: #9dff9d;
}
QHeaderView::section {
    background-color: #16261a;
    color: #7dff9a;
    border: none;
    border-right: 1px solid #2c4a2c;
    border-bottom: 1px solid #2c4a2c;
    padding: 10px 12px;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
}
QTableCornerButton::section {
    background-color: #16261a;
    border: none;
}
QScrollBar:vertical {
    background: #0a0c0a;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2c4a2c;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3f6a3f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QLabel#guideBody {
    color: #b9d9b9;
    font-size: 13px;
}
QLabel#guideNote {
    color: #ffcc44;
    font-size: 12px;
}
"""


STEPS_TEXT = (
    "<p><b>1. Запуск базового реактора.</b> В главном меню выберите "
    "«Новая игра (песочница)». В начале стержни опущены полностью, реактор "
    "заглушен, мощность почти нулевая. Кредиты начисляются только за "
    "выработку электроэнергии, поэтому первая задача — выйти на мощность.</p>"
    "<p><b>2. Стержни на 70–75 %.</b> Плавно выводите стержни, "
    "поднимая их до 70–75 % и не перескакивая сразу на максимум. На этом "
    "участке реактивность ещё отрицательная или близка к нулю, и вы "
    "успеваете увидеть реакцию реактора на каждое движение.</p>"
    "<p><b>3. Охлаждение на 100 %.</b> Расход теплоносителя должен быть "
    "полным: 100 % на насосах первого контура. Так температура топлива и "
    "давление остаются в безопасной зоне, пока реактор разгоняется.</p>"
    "<p><b>4. Дождитесь мощности.</b> Мощность растёт с задержкой: сначала "
    "тепловая, затем электрическая. Ориентир для базового чертежа — "
    "10–40 МВт тепловой мощности, то есть примерно 3–12 МВт электрической. "
    "Если мощность не растёт, выведите стержни ещё на 2–3 %; если растёт "
    "слишком быстро — сразу верните их обратно.</p>"
    "<p><b>5. Копите кредиты.</b> Каждую секунду работы на мощности вы "
    "получаете кредиты. Первые накопления лучше потратить на модули и "
    "чертежи под средний реактор: базовый даёт немного, но стабильно.</p>"
    "<p>Помните про ксенон: через несколько минут после выхода на мощность "
    "он начинает «съедать» реактивность. Если мощность падает сама по себе — "
    "не гоните стержни до упора, а добавьте 1–3 % и подождите. Резкие "
    "движения на фоне ксенонового отравления — самая частая причина аварии.</p>"
)


MODULES_TEXT = (
    "<p><b>Готовые чертежи — это база.</b> Купленный чертёж даёт ровно те "
    "характеристики, что заявлены в магазине: предсказуемый реактор, "
    "который ведёт себя одинаково от запуска к запуску. Для первых шагов "
    "этого достаточно.</p>"
    "<p><b>Верфь даёт бонус.</b> Ручная сборка реактора в Верфи из "
    "отдельных модулей даёт +10–15 % к эффективности по сравнению с готовым "
    "чертежом того же уровня. Бонус тем выше, чем больше модулей вы "
    "поставили сами. Собранный вручную реактор сначала уходит на площадку "
    "(сборка занимает время), и только потом его можно запустить.</p>"
    "<p><b>Модули покупаются за кредиты.</b> Корпус, теплоноситель, стержни, "
    "системы защиты и турбины приобретаются в магазине за кредиты, заработанные "
    "на выработке. Купленный модуль остаётся у вас навсегда, поэтому сборка "
    "в Верфи — это долгосрочное вложение: дороже на старте, выгоднее на дистанции.</p>"
    "<p>Практический совет: сначала выжмите максимум из базового реактора, "
    "купите пару модулей, соберите средний реактор в Верфи и только затем "
    "переходите к готовым чертежам высокого уровня.</p>"
)


TABLE_HEADERS = ("Чертёж", "Стержни", "Охлаждение", "Ожидаемая мощность")

TABLE_ROWS = (
    ("Базовый", "70–75 %", "100 %", "10–40 МВт тепл. · 3–12 МВт эл."),
    ("Средний", "65–72 %", "100 %", "250–1000 МВт тепл. · 80–330 МВт эл."),
    ("Высокий", "60–70 %", "95–100 %", "5–20 ГВт тепл. · 1.8–7.2 ГВт эл."),
)

TABLE_NOTE = (
    "Значения приблизительные и даны для полностью исправного контура. "
    "После выхода на мощность уровень ксенона меняется, поэтому стержни "
    "приходится подправлять на 2–5 %. Держите температуру топлива ниже "
    "предела и следите за запасом по давлению."
)


class GuideWindow(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("РЕАКТОР — руководство")
        self.resize(900, 640)
        self.setStyleSheet(GUIDE_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(_header_frame("РУКОВОДСТВО", "КРАТКИЙ КУРС ОПЕРАТОРА"))

        tabs = QTabWidget()
        tabs.setObjectName("guideTabs")
        tabs.addTab(self._text_tab(STEPS_TEXT), "ПЕРВЫЕ ШАГИ")
        tabs.addTab(self._schemes_tab(), "СХЕМЫ РАБОТЫ")
        tabs.addTab(self._text_tab(MODULES_TEXT), "МОДУЛИ И ВЕРФЬ")
        root.addWidget(tabs, 1)

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

    def _text_tab(self, html):
        label = QLabel(html)
        label.setObjectName("guideBody")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(label)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _schemes_tab(self):
        table = QTableWidget(len(TABLE_ROWS), len(TABLE_HEADERS))
        table.setHorizontalHeaderLabels(list(TABLE_HEADERS))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.verticalHeader().setVisible(False)

        for row, values in enumerate(TABLE_ROWS):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, column, item)
            table.setRowHeight(row, 44)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setMinimumHeight(44 * (len(TABLE_ROWS) + 1) + 8)

        note = QLabel(TABLE_NOTE)
        note.setObjectName("guideNote")
        note.setWordWrap(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(table)
        layout.addWidget(note)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll
