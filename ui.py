"""Пульт управления (SCADA-подобный интерфейс) для симулятора реактора.

Модуль содержит только класс окна. Никакой цикл/таймер здесь не создаётся:
главный цикл приложения раз в секунду вызывает ``ReactorControlWindow.update_ui()``.
"""

from html import escape

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from audio import AudioEngine
from effects import AlarmLamp, ScreenPulse
from reactor_core import Reactor, create_reactor
from tutorial import TutorialCard, mark_tutorial_seen, tutorial_seen


COLOR_BG = "#121212"
COLOR_TEXT = "#c9f5c9"
COLOR_DIM = "#6d8a6d"
COLOR_OK = "#22ff77"
COLOR_WARN = "#ffcc33"
COLOR_ALARM = "#ff2d2d"
COLOR_COOL = "#39c6ff"

WARN_RATIO = 0.80
CRIT_RATIO = 1.00

STATE_NAMES = {
    "cold": "ХОЛОДНЫЙ",
    "shutdown": "ЗАГЛУШЕН",
    "critical": "КРИТИЧЕСКИЙ",
    "supercritical": "НАДКРИТИЧЕСКИЙ",
    "scram": "АЗ-5 / ГЛУШЕНИЕ",
    "meltdown": "РАСПЛАВЛЕНИЕ",
}

STATE_COLORS = {
    "cold": COLOR_COOL,
    "shutdown": "#8fa6c8",
    "critical": COLOR_OK,
    "supercritical": COLOR_WARN,
    "scram": "#ff9a1f",
    "meltdown": COLOR_ALARM,
}

FAILURE_NAMES = {
    "none": "нет",
    "overheat": "перегрев топлива",
    "overpressure": "разрыв контура по давлению",
    "overpower": "превышение мощности",
    "prompt_critical": "мгновенная критичность",
}

WEAR_NAMES = {
    "hull": "КОРПУС",
    "fuel": "ТОПЛИВО",
    "rods": "СТЕРЖНИ",
    "pump": "НАСОС",
    "turbine": "ТУРБИНА",
    "shield": "ЗАЩИТА",
}

WEAR_WARN_PCT = 60.0
WEAR_CRIT_PCT = 30.0


QSS = """
QWidget {
    background-color: #121212;
    color: #c9f5c9;
    font-family: "Consolas", "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 13px;
}
QFrame#headerFrame {
    background-color: #0d100d;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
}
QGroupBox {
    background-color: #161816;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    margin-top: 20px;
    padding: 12px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #7dff9a;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}
QLabel#titleLabel {
    color: #9dff9d;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 3px;
}
QLabel#subTitle {
    color: #7fa07f;
    font-size: 13px;
}
QLabel#stateLabel {
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel#wearLabel {
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel#headerInfo {
    color: #7fa07f;
    font-size: 13px;
}
QLabel#sensorName {
    color: #8fb48f;
    font-size: 14px;
    letter-spacing: 1px;
}
QLabel#sensorValue {
    font-size: 28px;
    font-weight: bold;
}
QLabel#sensorLimit {
    color: #5f7a5f;
    font-size: 12px;
}
QLabel#controlTitle {
    color: #8fb48f;
    font-size: 14px;
    letter-spacing: 1px;
}
QLabel#controlValue {
    color: #d8ffd8;
    font-size: 20px;
    font-weight: bold;
}
QLabel#hint {
    color: #6d8a6d;
    font-size: 12px;
}
QProgressBar {
    background-color: #0a0c0a;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    min-height: 22px;
}
QProgressBar::chunk {
    background-color: #22ff77;
    border-radius: 3px;
}
QSlider::groove:horizontal {
    height: 10px;
    background: #0a0c0a;
    border: 1px solid #2c4a2c;
    border-radius: 5px;
}
QSlider::sub-page:horizontal {
    background: #1f6f3f;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    width: 26px;
    margin: -9px 0;
    border-radius: 4px;
    background: #22ff77;
    border: 2px solid #0a0c0a;
}
QSlider::handle:horizontal:hover {
    background: #7dff9a;
}
QSlider::handle:horizontal:disabled {
    background: #3a4a3a;
}
QSlider::sub-page:horizontal:disabled {
    background: #243024;
}
QPushButton#panelButton {
    background-color: #16261a;
    color: #9dff9d;
    border: 1px solid #2c4a2c;
    border-radius: 4px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 2px;
}
QPushButton#panelButton:hover {
    background-color: #1f3a24;
    border-color: #3f6a3f;
}
QPushButton#panelButton:checked {
    background-color: #6a4a06;
    color: #ffd966;
    border-color: #ffcc33;
}
QPushButton#scramButton {
    background-color: #7a0b0b;
    color: #ffecec;
    border: 3px solid #ff2d2d;
    border-radius: 8px;
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 18px 26px;
}
QPushButton#scramButton:hover {
    background-color: #a81212;
}
QPushButton#scramButton:pressed {
    background-color: #560606;
}
QPushButton#scramButton:disabled {
    background-color: #2a1414;
    color: #7a4a4a;
    border-color: #4a1f1f;
}
QTextEdit#logView {
    background-color: #0b0d0b;
    border: 1px solid #2c4a2c;
    color: #b9e6b9;
    font-size: 13px;
    selection-background-color: #1f6f3f;
}
QScrollBar:vertical {
    background: #121212;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2c4a2c;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3f6a3f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #121212;
}
"""


WATERMARK_QSS = """
QWidget#watermarkOverlay {
    background: transparent;
}
QPushButton#watermarkBadge {
    background-color: rgba(20, 20, 24, 110);
    color: rgba(190, 160, 255, 160);
    border: 1px solid rgba(150, 110, 255, 80);
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 12px;
    letter-spacing: 1px;
}
QPushButton#watermarkBadge:hover {
    background-color: rgba(40, 32, 60, 170);
    color: rgba(214, 192, 255, 230);
}
QPushButton#watermarkButton {
    background-color: rgba(22, 20, 30, 170);
    color: #b18cff;
    border: 1px solid rgba(150, 110, 255, 110);
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 12px;
}
QPushButton#watermarkButton:hover {
    background-color: rgba(48, 38, 72, 200);
    color: #cbb0ff;
}
"""


class _WatermarkOverlay(QWidget):
    """Полупрозрачная плашка @Sners1 в правом нижнем углу поверх лога."""

    LINK = "https://t.me/Sners1"
    USERNAME = "@Sners1"
    MARGIN = 26

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("watermarkOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(WATERMARK_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.badge = QPushButton("@Sners1")
        self.badge.setObjectName("watermarkBadge")
        self.badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.badge.setToolTip("Меню автора")
        self.badge.clicked.connect(self._expand)

        self.title_button = QPushButton("@Sners1")
        self.title_button.setObjectName("watermarkButton")
        self.title_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_button.clicked.connect(self._copy_username)

        self.link_button = QPushButton("Скопировать ссылку")
        self.link_button.setObjectName("watermarkButton")
        self.link_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_button.clicked.connect(self._copy_link)

        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        layout.addWidget(self.badge, 0, align)
        layout.addWidget(self.title_button, 0, align)
        layout.addWidget(self.link_button, 0, align)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(2000)
        self._reset_timer.timeout.connect(self._reset_link_text)

        self._collapse()

    def _expand(self):
        self._reset_timer.stop()
        self.badge.setVisible(False)
        self.title_button.setText(self.USERNAME)
        self.title_button.setVisible(True)
        self.link_button.setText("Скопировать ссылку")
        self.link_button.setVisible(True)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.reposition()

    def _collapse(self):
        self._reset_timer.stop()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self.title_button.setVisible(False)
        self.link_button.setVisible(False)
        self.title_button.setText(self.USERNAME)
        self.link_button.setText("Скопировать ссылку")
        self.badge.setVisible(True)
        self.reposition()

    def _is_inside(self, obj):
        widget = obj if isinstance(obj, QWidget) else None
        while widget is not None:
            if widget is self:
                return True
            widget = widget.parentWidget()
        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and not self._is_inside(obj):
            self._collapse()
        return super().eventFilter(obj, event)

    def _copy_username(self):
        QApplication.clipboard().setText(self.USERNAME)
        self.title_button.setText("Скопировано!")
        self.reposition()
        self._reset_timer.start()

    def _copy_link(self):
        QApplication.clipboard().setText(self.LINK)
        self.link_button.setText("Скопировано!")
        self.reposition()
        self._reset_timer.start()

    def _reset_link_text(self):
        self._collapse()

    def reposition(self):
        """Подогнать размер под содержимое и прижаться к правому нижнему углу."""
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            self.move(
                parent.width() - self.width() - self.MARGIN,
                parent.height() - self.height() - self.MARGIN,
            )
        self.raise_()


def _lamp_level(ratio):
    if ratio >= CRIT_RATIO:
        return 2
    if ratio >= WARN_RATIO:
        return 1
    return 0


class _Sensor:
    """Виджеты одного индикатора: число, предел и полоска."""

    __slots__ = ("value", "limit", "bar", "text_color", "bar_color")

    def __init__(self, value, limit, bar):
        self.value = value
        self.limit = limit
        self.bar = bar
        self.text_color = None
        self.bar_color = None


class ReactorControlWindow(QWidget):
    """Тёмный SCADA-пульт для объекта :class:`reactor_core.Reactor`."""

    pause_toggled = Signal(bool)
    menu_requested = Signal()
    destroyed = Signal()

    def __init__(self, reactor=None, parent=None):
        super().__init__(parent)
        if reactor is None:
            reactor = create_reactor("base")
        if not isinstance(reactor, Reactor):
            raise TypeError("reactor must be a Reactor instance")

        self.reactor = reactor
        self._prev = None
        self._last_state = None
        self._last_state_color = None
        self._flags = {}
        self._power_trend = 0
        self._last_xenon_log = -1.0e9
        self._syncing = False
        self._paused = False
        self._critical_active = False
        self._wear_blink_on = True
        self._wear_critical = False
        self._wear_last_text = None

        self.audio = AudioEngine(self)
        self.audio.set_muted(bool(getattr(reactor, 'muted', False)))

        self.setWindowTitle("Пульт управления — %s" % reactor.blueprint.name)
        self.resize(1180, 880)
        self.setStyleSheet(QSS)

        self._wear_timer = QTimer(self)
        self._wear_timer.setInterval(500)
        self._wear_timer.timeout.connect(self._blink_wear)

        self._build_layout()
        self._sync_controls(reactor.snapshot())
        self._log(
            "Пульт подключён: %s · реализм %s · масштаб времени ×%g"
            % (reactor.blueprint.name, reactor.realism.level.value, reactor.time_scale),
            COLOR_COOL,
        )
        self.update_ui()

    # ------------------------------------------------------------------ build

    def _build_layout(self):
        root = QVBoxLayout(self)
        self._root_layout = root
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_header())
        root.addWidget(self._build_sensors())
        root.addWidget(self._build_controls(), 1)
        root.addWidget(self._build_log(), 1)

        self.pulse = ScreenPulse(self)
        self._build_lamps()
        self._build_tutorial()

        self.watermark = _WatermarkOverlay(self)
        self.watermark.setParent(self)
        self.watermark.show()
        self.watermark.raise_()
        self.watermark.reposition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        overlay = getattr(self, "watermark", None)
        if overlay is not None:
            overlay.reposition()
            overlay.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        overlay = getattr(self, "watermark", None)
        if overlay is not None:
            overlay.reposition()
            overlay.raise_()

    def _build_lamps(self):
        bar = QFrame()
        bar.setObjectName("lampBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)
        self.lamp_temp = AlarmLamp("ТЕМП")
        self.lamp_press = AlarmLamp("ДАВЛ")
        self.lamp_power = AlarmLamp("МОЩН")
        self.lamp_xenon = AlarmLamp("КСЕНОН")
        self.lamp_scram = AlarmLamp("АЗ-5")
        for lamp in (
            self.lamp_temp,
            self.lamp_press,
            self.lamp_power,
            self.lamp_xenon,
            self.lamp_scram,
        ):
            layout.addWidget(lamp)
        layout.addStretch(1)
        self._lamp_bar = bar
        self._root_layout.insertWidget(1, bar)

    def _update_lamps(self, snap, fuel_ratio, press_ratio, power_ratio, xenon_pct):
        self.lamp_temp.set_level(_lamp_level(fuel_ratio))
        self.lamp_press.set_level(_lamp_level(press_ratio))
        self.lamp_power.set_level(_lamp_level(power_ratio))
        self.lamp_xenon.set_level(2 if xenon_pct >= 90.0 else (1 if xenon_pct >= 70.0 else 0))
        scram = snap["state"] == "scram" or snap["destroyed"]
        self.lamp_scram.set_level(2 if scram else 0)

    def _build_tutorial(self):
        steps = [
            (
                "УПРАВЛЯЮЩИЕ СТЕРЖНИ",
                "Стержни поглощают нейтроны и гасят цепную реакцию. Чем сильнее они "
                "погружены, тем ниже реактивность и мощность. Выдвигайте их плавно: "
                "резкий вывод даёт разгон, а на малой мощности — опасный паровой "
                "коэффициент реактивности.",
                self.rod_slider,
            ),
            (
                "ОХЛАЖДЕНИЕ",
                "Подача теплоносителя снимает тепло с топлива. Мало охлаждения — "
                "рост температуры и давления, вскипание и разрыв контура. Больше "
                "охлаждения — быстрее нагрев и падение температуры топлива.",
                self.coolant_slider,
            ),
            (
                "АВАРИЙНАЯ ЗАЩИТА (SCRAM)",
                "Кнопка АЗ-5 мгновенно вводит все стержни в активную зону и "
                "глушит реактор. Используйте её, когда параметры подходят к пределу "
                "или когда вы потеряли контроль над реактивностью.",
                self.scram_button,
            ),
            (
                "ДАТЧИКИ",
                "Следите за температурой топлива, давлением и мощностью. Красный "
                "цвет означает близость к аварийному пределу. Ксенон отравляет "
                "реактор после снижения мощности и мешает повторному запуску.",
                self.fuel_sensor.bar,
            ),
            (
                "ЛОГ СОБЫТИЙ",
                "Журнал подскажет, что происходит: предупреждения о приближении к "
                "пределам, аварии и действия экипажа фиксируются с метками времени.",
                self.log_view,
            ),
        ]
        self.tutorial = TutorialCard(self, steps)
        self.tutorial.finished.connect(self._on_tutorial_finished)
        if not tutorial_seen():
            QTimer.singleShot(400, self.start_tutorial)

    def start_tutorial(self):
        self.tutorial.start()

    def _on_tutorial_finished(self):
        mark_tutorial_seen()

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)

        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("ПУЛЬТ УПРАВЛЕНИЯ РЕАКТОРОМ")
        title.setObjectName("titleLabel")
        sub = QLabel(
            "%s · реализм %s · ×%g"
            % (
                self.reactor.blueprint.name.upper(),
                self.reactor.realism.level.value,
                self.reactor.time_scale,
            )
        )
        sub.setObjectName("subTitle")
        self.state_label = QLabel("—")
        self.state_label.setObjectName("stateLabel")
        self.wear_label = QLabel("СОСТОЯНИЕ: —")
        self.wear_label.setObjectName("wearLabel")
        left.addWidget(title)
        left.addWidget(sub)
        left.addWidget(self.state_label)
        left.addWidget(self.wear_label)

        self.header_info = QLabel("")
        self.header_info.setObjectName("headerInfo")
        self.header_info.setWordWrap(True)
        self.header_info.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )

        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        self.pause_button = QPushButton("ПАУЗА")
        self.pause_button.setObjectName("panelButton")
        self.pause_button.setCheckable(True)
        self.pause_button.setMinimumWidth(120)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.menu_button = QPushButton("В МЕНЮ")
        self.menu_button.setObjectName("panelButton")
        self.menu_button.setMinimumWidth(120)
        self.menu_button.clicked.connect(self.menu_requested.emit)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.menu_button)

        layout.addLayout(left, 0)
        layout.addWidget(self.header_info, 1)
        layout.addLayout(buttons, 0)
        return frame

    def _build_sensors(self):
        group = QGroupBox("ДАТЧИКИ")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(16, 20, 16, 14)

        self.fuel_sensor = self._add_sensor(grid, 0, "Температура топлива")
        self.pressure_sensor = self._add_sensor(grid, 1, "Давление в контуре")
        self.power_sensor = self._add_sensor(grid, 2, "Мощность (тепловая)")
        self.xenon_sensor = self._add_sensor(grid, 3, "Уровень ксенона")
        grid.setColumnStretch(3, 1)
        return group

    def _add_sensor(self, grid, row, title):
        name = QLabel(title)
        name.setObjectName("sensorName")

        value = QLabel("—")
        value.setObjectName("sensorValue")
        value.setMinimumWidth(220)
        value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        limit = QLabel("")
        limit.setObjectName("sensorLimit")
        limit.setMinimumWidth(170)

        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setMinimumHeight(22)
        bar.setMinimumWidth(320)

        grid.addWidget(name, row, 0)
        grid.addWidget(value, row, 1)
        grid.addWidget(limit, row, 2)
        grid.addWidget(bar, row, 3)
        return _Sensor(value, limit, bar)

    def _build_controls(self):
        group = QGroupBox("ОРГАНЫ УПРАВЛЕНИЯ")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(16, 22, 16, 14)
        layout.setSpacing(24)

        sliders = QVBoxLayout()
        sliders.setSpacing(18)
        rods_box, self.rod_slider, self.rod_value = self._make_slider_block(
            "УПРАВЛЯЮЩИЕ СТЕРЖНИ (погружение)", self.reactor.rod_position
        )
        coolant_box, self.coolant_slider, self.coolant_value = self._make_slider_block(
            "ПОДАЧА ОХЛАЖДЕНИЯ", self.reactor.coolant_flow
        )
        sliders.addWidget(rods_box)
        sliders.addWidget(coolant_box)
        sliders.addStretch(1)

        self.rod_slider.valueChanged.connect(self._on_rods_changed)
        self.coolant_slider.valueChanged.connect(self._on_coolant_changed)

        scram_box = QVBoxLayout()
        scram_box.setSpacing(6)
        self.scram_button = QPushButton("АЗ-5\nSCRAM")
        self.scram_button.setObjectName("scramButton")
        self.scram_button.setMinimumHeight(120)
        self.scram_button.setMinimumWidth(260)
        self.scram_button.clicked.connect(self._on_scram)
        hint = QLabel("Аварийная защита: полный ввод стержней")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        scram_box.addWidget(self.scram_button, 1)
        scram_box.addWidget(hint)

        layout.addLayout(sliders, 3)
        layout.addLayout(scram_box, 1)
        return group

    def _make_slider_block(self, title, fraction):
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        head = QHBoxLayout()
        caption = QLabel(title)
        caption.setObjectName("controlTitle")
        value = QLabel("%d %%" % int(round(fraction * 100)))
        value.setObjectName("controlValue")
        head.addWidget(caption)
        head.addStretch(1)
        head.addWidget(value)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(round(fraction * 100)))
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setMinimumHeight(38)

        layout.addLayout(head)
        layout.addWidget(slider)
        return box, slider, value

    def _build_log(self):
        group = QGroupBox("ЛОГ СОБЫТИЙ")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 20, 12, 10)
        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(170)
        self.log_view.document().setMaximumBlockCount(1000)
        layout.addWidget(self.log_view)
        return group

    # --------------------------------------------------------------- controls

    @property
    def paused(self):
        return self._paused

    def closeEvent(self, event):
        self.audio.stop()
        self.pulse.set_active(False)
        super().closeEvent(event)

    def set_paused(self, paused):
        paused = bool(paused)
        if paused == self._paused:
            return
        self._paused = paused
        self.pause_button.blockSignals(True)
        self.pause_button.setChecked(paused)
        self.pause_button.blockSignals(False)
        self.pause_button.setText("ПРОДОЛЖИТЬ" if paused else "ПАУЗА")
        self.audio.play_click(0.30)
        self._log(
            "Симуляция приостановлена" if paused else "Симуляция продолжена",
            COLOR_WARN if paused else COLOR_OK,
        )
        self.pause_toggled.emit(paused)

    def _on_pause_clicked(self):
        self.set_paused(not self._paused)

    def _on_rods_changed(self, value):
        if self._syncing:
            return
        self.audio.play_click(0.22)
        self.rod_value.setText("%d %%" % value)
        if not self.reactor.set_rod_position(value / 100.0):
            self._log(
                "Стержни заблокированы: активна АЗ-5 или реактор разрушен",
                COLOR_WARN,
            )
            self._sync_controls(self.reactor.snapshot())

    def _on_coolant_changed(self, value):
        if self._syncing:
            return
        self.audio.play_click(0.18)
        self.coolant_value.setText("%d %%" % value)
        if not self.reactor.set_coolant_flow(value / 100.0):
            self._log("Насосы охлаждения недоступны: реактор разрушен", COLOR_WARN)
            self._sync_controls(self.reactor.snapshot())

    def _on_scram(self):
        self.audio.play_click(0.55)
        if self.reactor.scram():
            self._log(
                "АЗ-5: АВАРИЙНАЯ ЗАЩИТА АКТИВИРОВАНА — все стержни введены",
                COLOR_ALARM,
            )
            self._sync_controls(self.reactor.snapshot())
        else:
            self._log("АЗ-5 недоступна: реактор разрушен", COLOR_WARN)

    def _sync_controls(self, snap):
        self._syncing = True
        try:
            self._apply_slider(self.rod_slider, self.rod_value, snap["rod_position"])
            self._apply_slider(
                self.coolant_slider, self.coolant_value, snap["coolant_flow"]
            )
        finally:
            self._syncing = False

        locked = snap["destroyed"] or snap["state"] == "scram"
        self.rod_slider.setEnabled(not locked)
        self.coolant_slider.setEnabled(not snap["destroyed"])
        self.scram_button.setEnabled(not locked)

    @staticmethod
    def _apply_slider(slider, label, fraction):
        if slider.isSliderDown():
            return
        value = int(round(max(0.0, min(1.0, fraction)) * 100))
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        label.setText("%d %%" % value)

    # ------------------------------------------------------------------- loop

    def update_ui(self):
        """Забрать свежий снимок реактора и обновить датчики, лог и органы управления.

        Вызывается главным циклом приложения (например, раз в секунду).
        """
        snap = self.reactor.snapshot()

        self._update_header(snap)
        self._update_wear(snap)

        fuel_limit = self.reactor.temp_limit_effective
        pressure_limit = self.reactor.pressure_limit_effective
        thermal_limit = self._thermal_power_limit()
        xenon_pct = self._xenon_percent(snap)

        self._set_sensor(self.fuel_sensor, snap["fuel_temp"], fuel_limit, "°C", 1)
        self._set_sensor(
            self.pressure_sensor, snap["pressure"], pressure_limit, "МПа", 2
        )
        self._set_sensor(
            self.power_sensor, snap["thermal_power_mw"], thermal_limit, "МВт", 1
        )
        self._set_sensor(self.xenon_sensor, xenon_pct, 100.0, "%", 0)

        fuel_ratio = snap["fuel_temp"] / fuel_limit if fuel_limit > 0 else 0.0
        press_ratio = snap["pressure"] / pressure_limit if pressure_limit > 0 else 0.0
        power_ratio = snap["thermal_power_mw"] / thermal_limit if thermal_limit > 0 else 0.0

        self._update_lamps(snap, fuel_ratio, press_ratio, power_ratio, xenon_pct)
        self.audio.update(
            fuel_ratio,
            press_ratio,
            power_ratio,
            xenon_pct / 100.0,
            any(v >= 2 for v in self._lamp_levels()),
            snap["destroyed"],
        )
        critical = max(fuel_ratio, press_ratio, power_ratio) >= CRIT_RATIO
        self.pulse.set_active(critical or snap["destroyed"])

        self._sync_controls(snap)
        self._process_events(snap, fuel_limit, pressure_limit, thermal_limit, xenon_pct)
        self._prev = snap

    def _lamp_levels(self):
        return (
            self.lamp_temp.level(),
            self.lamp_press.level(),
            self.lamp_power.level(),
            self.lamp_xenon.level(),
            self.lamp_scram.level(),
        )

    def _update_header(self, snap):
        state = snap["state"]
        self.state_label.setText(STATE_NAMES.get(state, str(state).upper()))
        color = STATE_COLORS.get(state, COLOR_TEXT)
        if color != self._last_state_color:
            self._last_state_color = color
            self.state_label.setStyleSheet("color: %s;" % color)

        period = snap["period_s"]
        period_text = "∞" if period is None else "%.1f с" % period
        self.header_info.setText(
            "время %s   |   ρ = %+.1f pcm (%+.3f $)   |   период %s\n"
            "эл. %.1f МВт из %.0f МВт   |   теплоноситель %.1f °C / насыщение %.1f °C"
            % (
                self._fmt_time(snap["time"]),
                snap["reactivity_pcm"],
                snap["reactivity_dollars"],
                period_text,
                snap["electrical_power_mw"],
                snap["rated_power_mw"],
                snap["coolant_temp"],
                snap["saturation_temp"],
            )
        )

    def _update_wear(self, snap):
        """Общее состояние прочности реактора и мигание при аварии."""
        pct = max(0.0, min(1.0, float(snap.get("wear_overall", 1.0)))) * 100.0
        broken = list(snap.get("broken") or ())
        wear = snap.get("wear") or {}
        damaged = [
            WEAR_NAMES.get(key, key.upper())
            for key, value in wear.items()
            if float(value) * 100.0 <= WEAR_CRIT_PCT
        ]
        critical = pct <= WEAR_CRIT_PCT or bool(broken) or bool(damaged)

        text = "СОСТОЯНИЕ: %d %%" % int(round(pct))
        if broken or damaged:
            names = [WEAR_NAMES.get(key, key.upper()) for key in broken] + damaged
            text += " (%s)" % ", ".join(dict.fromkeys(names))
            text += " — ТРЕБУЕТСЯ РЕМОНТ"
        elif pct <= WEAR_WARN_PCT:
            text += " (ТРЕБУЕТСЯ РЕМОНТ)"

        if critical:
            color = COLOR_ALARM
        elif pct <= WEAR_WARN_PCT:
            color = COLOR_WARN
        else:
            color = COLOR_OK

        if self._wear_last_text != text:
            self._wear_last_text = text
            self.wear_label.setText(text)

        self.wear_label.setStyleSheet(
            "color: %s;" % (color if (self._wear_blink_on or not critical) else COLOR_BG)
        )

        if critical != self._wear_critical:
            self._wear_critical = critical
            self._wear_blink_on = True
            if critical:
                self._wear_timer.start()
            else:
                self._wear_timer.stop()

    def _blink_wear(self):
        self._wear_blink_on = not self._wear_blink_on
        self._update_wear(self.reactor.snapshot())

    def _set_sensor(self, sensor, value, limit, unit, decimals):
        ratio = value / limit if limit > 0 else 0.0
        color = self._ratio_color(ratio)

        sensor.value.setText("%s %s" % (self._format_value(value, decimals), unit))
        sensor.limit.setText("предел %s %s" % (self._format_value(limit, decimals), unit))

        text_color = color if ratio >= WARN_RATIO else COLOR_TEXT
        if text_color != sensor.text_color:
            sensor.text_color = text_color
            sensor.value.setStyleSheet("color: %s;" % text_color)

        bar_value = int(round(max(0.0, min(1.0, ratio)) * 1000))
        sensor.bar.setValue(bar_value)
        if color != sensor.bar_color:
            sensor.bar_color = color
            sensor.bar.setStyleSheet(
                "QProgressBar::chunk { background-color: %s; border-radius: 3px; }"
                % color
            )
        sensor.bar.setToolTip("%.0f %% от предела" % (ratio * 100.0))

    # ------------------------------------------------------------------ events

    def _process_events(self, snap, fuel_limit, pressure_limit, thermal_limit, xenon_pct):
        prev = self._prev

        state = snap["state"]
        if state != self._last_state:
            self._log(
                "Состояние реактора: %s" % STATE_NAMES.get(state, state),
                STATE_COLORS.get(state, COLOR_TEXT),
            )
            self._last_state = state

        if snap["destroyed"] and not self._flag("destroyed"):
            self._log(
                "КРИТИЧЕСКАЯ АВАРИЯ: %s. Реактор разрушен."
                % FAILURE_NAMES.get(snap["failure"], snap["failure"]),
                COLOR_ALARM,
            )

        if snap["prompt_critical"]:
            if not self._flag("prompt"):
                self._log(
                    "МГНОВЕННАЯ КРИТИЧНОСТЬ: ρ ≥ β — разгон на мгновенных нейтронах",
                    COLOR_ALARM,
                )
        else:
            self._flags["prompt"] = False

        fuel_ratio = snap["fuel_temp"] / fuel_limit if fuel_limit > 0 else 0.0
        self._limit_alarm(
            "fuel",
            fuel_ratio,
            "ТЕМПЕРАТУРА ТОПЛИВА",
            self._format_value(snap["fuel_temp"], 1) + " °C",
            self._format_value(fuel_limit, 1) + " °C",
        )

        press_ratio = snap["pressure"] / pressure_limit if pressure_limit > 0 else 0.0
        self._limit_alarm(
            "pressure",
            press_ratio,
            "ДАВЛЕНИЕ",
            self._format_value(snap["pressure"], 2) + " МПа",
            self._format_value(pressure_limit, 2) + " МПа",
        )

        power_ratio = (
            snap["thermal_power_mw"] / thermal_limit if thermal_limit > 0 else 0.0
        )
        self._limit_alarm(
            "power",
            power_ratio,
            "МОЩНОСТЬ",
            self._format_value(snap["thermal_power_mw"], 1) + " МВт",
            self._format_value(thermal_limit, 1) + " МВт",
        )

        if xenon_pct >= 70.0:
            if not self._flags.get("xenon_high"):
                self._flags["xenon_high"] = True
                self._log(
                    "Ксеноновое отравление: %.0f %% (%.0f pcm)"
                    % (xenon_pct, snap["xenon_poison"] * 1.0e5),
                    COLOR_WARN,
                )
        elif xenon_pct < 60.0:
            self._flags["xenon_high"] = False

        if prev is not None:
            prev_xenon = self._xenon_percent(prev)
            if (
                xenon_pct - prev_xenon > 0.1
                and snap["time"] - self._last_xenon_log >= 15.0
            ):
                self._last_xenon_log = snap["time"]
                self._log(
                    "Ксеноновое отравление растет: %.0f %%" % xenon_pct, COLOR_WARN
                )

            delta = snap["thermal_power_mw"] - prev["thermal_power_mw"]
            deadband = max(thermal_limit * 0.001, 0.05)
            if delta > deadband:
                trend = 1
            elif delta < -deadband:
                trend = -1
            else:
                trend = 0
            if trend > 0 and trend != self._power_trend:
                self._log(
                    "Мощность растет: %.1f МВт (тепл.)" % snap["thermal_power_mw"],
                    COLOR_WARN,
                )
                self._power_trend = trend
            elif trend < 0 and trend != self._power_trend:
                self._log(
                    "Мощность снижается: %.1f МВт (тепл.)" % snap["thermal_power_mw"],
                    COLOR_COOL,
                )
                self._power_trend = trend
            elif trend == 0:
                self._power_trend = 0

        period = snap["period_s"]
        if period is not None and 0.0 < period < 10.0:
            if not self._flags.get("fast_period"):
                self._flags["fast_period"] = True
                self._log("Опасно короткий период разгона: %.1f с" % period, COLOR_ALARM)
        elif period is None or period > 20.0:
            self._flags["fast_period"] = False

        if snap["overlimit_time"] > 0.0:
            if not self._flags.get("overlimit"):
                self._flags["overlimit"] = True
                self._log(
                    "Зафиксировано превышение пределов: идет отсчет до разрушения",
                    COLOR_ALARM,
                )
        else:
            self._flags["overlimit"] = False

    def _limit_alarm(self, key, ratio, title, current, limit_text):
        if ratio >= CRIT_RATIO:
            if not self._flags.get(key + "_crit"):
                self._flags[key + "_crit"] = True
                self._log(
                    "%s: ПРЕДЕЛ ПРЕВЫШЕН (%s ≥ %s)" % (title, current, limit_text),
                    COLOR_ALARM,
                )
        elif ratio < 0.97:
            self._flags[key + "_crit"] = False

        if ratio >= 0.90:
            if not self._flags.get(key + "_warn"):
                self._flags[key + "_warn"] = True
                self._log(
                    "%s: приближение к пределу (%s, %.0f %%)"
                    % (title, current, ratio * 100.0),
                    COLOR_WARN,
                )
        elif ratio < 0.85:
            self._flags[key + "_warn"] = False

    # ------------------------------------------------------------------- utils

    def _thermal_power_limit(self):
        blueprint = self.reactor.blueprint
        scale = self.reactor.realism.limit_scale
        return self.reactor.q_rated * blueprint.max_power * scale / blueprint.rated_power

    def _xenon_percent(self, snap):
        worth = self.reactor.blueprint.xenon_worth * self.reactor.realism.xenon_scale
        if worth <= 0.0:
            return 0.0
        return min(100.0, 100.0 * snap["xenon_poison"] / worth)

    def _flag(self, key):
        """Вернуть True, если событие уже было зарегистрировано; иначе отметить его."""
        if self._flags.get(key):
            return True
        self._flags[key] = True
        return False

    @staticmethod
    def _ratio_color(ratio):
        if ratio >= CRIT_RATIO:
            return COLOR_ALARM
        if ratio >= WARN_RATIO:
            return COLOR_WARN
        return COLOR_OK

    @staticmethod
    def _format_value(value, decimals):
        return ("%%.%df" % decimals % value).replace(",", " ")

    @staticmethod
    def _fmt_time(seconds):
        total = int(seconds)
        return "%02d:%02d:%02d" % (total // 3600, (total % 3600) // 60, total % 60)

    def _log(self, message, color=COLOR_TEXT):
        stamp = self._fmt_time(self.reactor.time)
        self.log_view.append(
            '<span style="color:%s">[%s]</span> '
            '<span style="color:%s">%s</span>'
            % (COLOR_DIM, stamp, color, escape(message))
        )
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)


ReactorWindow = ReactorControlWindow
