from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from audio import AudioEngine
from economy import format_credits
from settings import REALISM_DESCRIPTIONS, REALISM_NAMES, REALISM_ORDER


MENU_QSS = """
QWidget {
    background-color: #121212;
    color: #c9f5c9;
    font-family: "Consolas", "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 13px;
}
QFrame#menuFrame {
    background-color: #0d100d;
    border: 1px solid #2c4a2c;
    border-radius: 6px;
}
QLabel#menuTitle {
    color: #9dff9d;
    font-size: 34px;
    font-weight: bold;
    letter-spacing: 8px;
}
QLabel#menuSubtitle {
    color: #5f7a5f;
    font-size: 12px;
    letter-spacing: 3px;
}
QLabel#menuFooter {
    color: #4d634d;
    font-size: 11px;
    letter-spacing: 1px;
}
QLabel#sectionTitle {
    color: #7dff9a;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}
QLabel#sectionHint {
    color: #6d8a6d;
    font-size: 12px;
}
QLabel#balanceLabel {
    color: #9dff9d;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 3px;
}
QLabel#errorLabel {
    color: #ff2d2d;
    font-size: 12px;
}
QPushButton#menuButton {
    background-color: #16261a;
    color: #b9e6b9;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    padding: 14px 18px;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 3px;
    text-align: left;
}
QPushButton#menuButton:hover {
    background-color: #1f3a24;
    border-color: #3f6a3f;
    color: #9dff9d;
}
QPushButton#menuButton:pressed {
    background-color: #0f1a11;
}
QPushButton#menuButton:disabled {
    background-color: #141614;
    color: #4a5a4a;
    border-color: #1f2a1f;
}
QPushButton#primaryButton {
    background-color: #1f6f3f;
    color: #eaffea;
    border: 1px solid #22ff77;
    border-radius: 4px;
    padding: 14px 18px;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 3px;
    text-align: left;
}
QPushButton#primaryButton:hover {
    background-color: #278a4e;
}
QPushButton#primaryButton:pressed {
    background-color: #175230;
}
QPushButton#menuButtonSmall {
    background-color: #16261a;
    color: #9dff9d;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 2px;
}
QPushButton#menuButtonSmall:hover {
    background-color: #1f3a24;
    border-color: #3f6a3f;
}
QComboBox {
    background-color: #0a0c0a;
    color: #c9f5c9;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    padding: 6px 10px;
}
QComboBox:hover {
    border-color: #3f6a3f;
}
QComboBox:disabled {
    color: #4a5a4a;
    border-color: #1f2a1f;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #0d100d;
    color: #c9f5c9;
    border: 1px solid #2c4a2c;
    outline: none;
    selection-background-color: #1f3a24;
    selection-color: #9dff9d;
}
QComboBox QAbstractItemView::item:disabled {
    color: #55624f;
    background-color: #0a0c0a;
}
QFrame#shopCard {
    background-color: #0b0e0b;
    border: 1px solid #24361f;
    border-radius: 6px;
}
QFrame#shopCardOwned {
    background-color: #0d140d;
    border: 1px solid #3f6a3f;
    border-radius: 6px;
}
QLabel#shopName {
    color: #9dff9d;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel#shopTier {
    color: #6d8a6d;
    font-size: 11px;
    letter-spacing: 2px;
}
QLabel#shopTagline {
    color: #8fb98f;
    font-size: 12px;
}
QLabel#shopDesc {
    color: #6d8a6d;
    font-size: 12px;
}
QLabel#shopStats {
    color: #a8d8a8;
    font-size: 12px;
}
QLabel#shopPrice {
    color: #ffcc44;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QRadioButton {
    color: #c9f5c9;
    font-size: 14px;
    padding: 8px 4px;
    spacing: 10px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3f6a3f;
    border-radius: 8px;
    background: #0a0c0a;
}
QRadioButton::indicator:checked {
    background: #22ff77;
    border-color: #7dff9a;
}
QRadioButton::indicator:hover {
    border-color: #7dff9a;
}
"""


def _header_frame(title_text, subtitle_text):
    frame = QFrame()
    frame.setObjectName("menuFrame")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(6)
    title = QLabel(title_text)
    title.setObjectName("menuTitle")
    subtitle = QLabel(subtitle_text)
    subtitle.setObjectName("menuSubtitle")
    if "<" in subtitle_text:
        subtitle.setTextFormat(Qt.TextFormat.RichText)
    layout.addWidget(title)
    layout.addWidget(subtitle)
    return frame


class MainMenuWindow(QWidget):
    new_game_requested = Signal()
    chernobyl_requested = Signal()
    shipyard_requested = Signal()
    shop_requested = Signal()
    guide_requested = Signal()
    history_requested = Signal()
    about_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, settings, state=None, load_error=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.state = state
        self.load_error = load_error
        self.audio = AudioEngine(self)
        self.setWindowTitle("РЕАКТОР — главное меню")
        self.resize(900, 640)
        self.setStyleSheet(MENU_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(
            _header_frame(
                "РЕАКТОР",
                'СИМУЛЯТОР УПРАВЛЕНИЯ ЯДЕРНЫМ РЕАКТОРОМ <span style="color:#ff2d2d;">beta</span>',
            )
        )
        root.addWidget(self._build_menu(), 1)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(10)

        copyright_label = QLabel("© 2026 Sners1")
        copyright_label.setObjectName("menuFooter")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        footer_row.addWidget(copyright_label)
        footer_row.addStretch(1)

        footer = QLabel("Beta build by Sners1")
        footer.setObjectName("menuFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_row.addWidget(footer)

        root.addLayout(footer_row)

        self.watermark_label = QLabel("@Sners1")
        self.watermark_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.watermark_label.setStyleSheet(
            "color: rgba(170, 140, 255, 90); font-size: 10px; letter-spacing: 1px;"
        )
        root.addWidget(self.watermark_label)

    def _build_menu(self):
        frame = QFrame()
        frame.setObjectName("menuFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        section = QLabel("ГЛАВНОЕ МЕНЮ")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        self.balance_label = QLabel("")
        self.balance_label.setObjectName("balanceLabel")
        layout.addWidget(self.balance_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.new_game_button = QPushButton("НОВАЯ ИГРА (ПЕСОЧНИЦА)")
        self.new_game_button.setObjectName("primaryButton")
        self.new_game_button.clicked.connect(lambda: self.audio.play_click())
        self.new_game_button.clicked.connect(self.new_game_requested.emit)
        layout.addWidget(self.new_game_button)

        self.scenario_button = QPushButton("СЦЕНАРИЙ: ЧЕРНОБЫЛЬ")
        self.scenario_button.setObjectName("menuButton")
        self.scenario_button.setEnabled(True)
        self.scenario_button.setToolTip("Запуск сценария на сложности «Хардкор»")
        self.scenario_button.clicked.connect(lambda: self.audio.play_click())
        self.scenario_button.clicked.connect(self._on_scenario_clicked)
        layout.addWidget(self.scenario_button)

        self.shipyard_button = QPushButton("ВЕРФЬ")
        self.shipyard_button.setObjectName("menuButton")
        self.shipyard_button.clicked.connect(lambda: self.audio.play_click())
        self.shipyard_button.clicked.connect(self.shipyard_requested.emit)
        layout.addWidget(self.shipyard_button)

        self.shop_button = QPushButton("МАГАЗИН ЧЕРТЕЖЕЙ")
        self.shop_button.setObjectName("menuButton")
        self.shop_button.clicked.connect(lambda: self.audio.play_click())
        self.shop_button.clicked.connect(self.shop_requested.emit)
        layout.addWidget(self.shop_button)

        self.guide_button = QPushButton("РУКОВОДСТВО")
        self.guide_button.setObjectName("menuButton")
        self.guide_button.clicked.connect(lambda: self.audio.play_click())
        self.guide_button.clicked.connect(self.guide_requested.emit)
        layout.addWidget(self.guide_button)

        self.history_button = QPushButton("ИСТОРИЯ РЕАКТОРОВ")
        self.history_button.setObjectName("menuButton")
        self.history_button.clicked.connect(lambda: self.audio.play_click())
        self.history_button.clicked.connect(self.history_requested.emit)
        layout.addWidget(self.history_button)

        self.about_button = QPushButton("О БИЛДЕ")
        self.about_button.setObjectName("menuButton")
        self.about_button.setToolTip("Информация о сборке и куда сообщать о багах")
        self.about_button.clicked.connect(lambda: self.audio.play_click())
        self.about_button.clicked.connect(self.about_requested.emit)
        layout.addWidget(self.about_button)

        self.settings_button = QPushButton("НАСТРОЙКИ")
        self.settings_button.setObjectName("menuButton")
        self.settings_button.clicked.connect(lambda: self.audio.play_click())
        self.settings_button.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_button)

        self.quit_button = QPushButton("ВЫХОД")
        self.quit_button.setObjectName("menuButton")
        self.quit_button.clicked.connect(lambda: self.audio.play_click())
        self.quit_button.clicked.connect(self.quit_requested.emit)
        layout.addWidget(self.quit_button)

        layout.addStretch(1)

        self.realism_label = QLabel("")
        self.realism_label.setObjectName("sectionHint")
        layout.addWidget(self.realism_label)
        self.refresh_realism()
        self.set_state(self.state, self.load_error)
        return frame

    def _on_scenario_clicked(self):
        self.chernobyl_requested.emit()

    def set_state(self, state, load_error=None):
        self.state = state
        self.load_error = load_error
        credits = 0.0 if state is None else state.credits
        self.balance_label.setText("КРЕДИТЫ: %s" % format_credits(credits))
        if load_error:
            self.error_label.setText(load_error)
            self.error_label.show()
        else:
            self.error_label.clear()
            self.error_label.hide()

    def closeEvent(self, event):
        self.audio.stop()
        super().closeEvent(event)

    def refresh_realism(self):
        level = self.settings.realism
        self.realism_label.setText(
            "ТЕКУЩИЙ УРОВЕНЬ РЕАЛИЗМА: %s" % REALISM_NAMES.get(level, level.value).upper()
        )


class SettingsWindow(QWidget):
    back_requested = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._radios = {}
        self.audio = AudioEngine(self)
        self.setWindowTitle("РЕАКТОР — настройки")
        self.resize(900, 640)
        self.setStyleSheet(MENU_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(_header_frame("НАСТРОЙКИ", "ПАРАМЕТРЫ СИМУЛЯЦИИ"))
        root.addWidget(self._build_body(), 1)

        back = QPushButton("НАЗАД")
        back.setObjectName("menuButtonSmall")
        back.clicked.connect(lambda: self.audio.play_click())
        back.clicked.connect(self.back_requested.emit)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(back)
        holder = QWidget()
        holder.setLayout(row)
        root.addWidget(holder)

    def closeEvent(self, event):
        self.audio.stop()
        super().closeEvent(event)

    def _build_body(self):
        frame = QFrame()
        frame.setObjectName("menuFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        section = QLabel("УРОВЕНЬ РЕАЛИЗМА")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        current = self.settings.realism
        for level in REALISM_ORDER:
            radio = QRadioButton(REALISM_NAMES[level].upper())
            radio.setChecked(level == current)
            radio.toggled.connect(
                lambda checked, lvl=level: self._on_realism_toggled(lvl, checked)
            )
            self._radios[level] = radio
            layout.addWidget(radio)

        self.realism_hint = QLabel("")
        self.realism_hint.setObjectName("sectionHint")
        self.realism_hint.setWordWrap(True)
        layout.addWidget(self.realism_hint)

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionHint")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        self._update_hint()
        return frame

    def _on_realism_toggled(self, level, checked):
        if not checked:
            self._update_hint()
            return
        if level == self.settings.realism:
            self._update_hint()
            self.status_label.setText("")
            return
        ok, error = self.settings.set_realism(level)
        if ok:
            self.status_label.setStyleSheet("color: #22ff77;")
            self.status_label.setText("Сохранено: %s" % REALISM_NAMES[level].upper())
        else:
            self.status_label.setStyleSheet("color: #ff2d2d;")
            self.status_label.setText(error or "Ошибка сохранения")
            previous = self.settings.realism
            radio = self._radios.get(previous)
            if radio is not None and not radio.isChecked():
                radio.blockSignals(True)
                radio.setChecked(True)
                radio.blockSignals(False)
        self._update_hint()

    def _update_hint(self):
        level = self.settings.realism
        self.realism_hint.setText(REALISM_DESCRIPTIONS.get(level, ""))
