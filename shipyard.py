import os

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from audio import AudioEngine
from economy import DEFAULT_BLUEPRINT, format_credits
from menu import MENU_QSS, _header_frame
from modules import (
    MAX_TIER_OFFSET,
    MODULES,
    SLOTS,
    SLOT_MODULES,
    assemble,
    assemble_cost,
    compare_with_ready,
)
from reactor_core import BLUEPRINTS, RealismLevel
from settings import SETTINGS_DIR
from wear_state import WEAR_FILENAME, WearState


SLOT_NAMES = {
    'hull': 'КОРПУС',
    'fuel': 'ТОПЛИВО',
    'rods': 'СТЕРЖНИ',
    'pump': 'НАСОС',
    'turbine': 'ТУРБИНА',
    'shield': 'ЗАЩИТА',
}

BUILD_NAME = 'Авторский чертёж'

LOCKED_TEXT = '#5a6a5a'
LOCKED_BG = '#0a0c0a'
LOCKED_HINT = 'Требуется чертёж более высокого уровня'


class ModuleItemDelegate(QStyledItemDelegate):
    """Рисует заблокированные модули серым и показывает подсказку."""

    def paint(self, painter, option, index):
        locked = index.data(Qt.ItemDataRole.ToolTipRole) == LOCKED_HINT
        if locked:
            option = QStyleOptionViewItem(option)
            option.state &= ~QStyle.StateFlag.State_Enabled
            option.palette.setColor(QPalette.ColorRole.Text, QColor(LOCKED_TEXT))
            option.palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(LOCKED_TEXT))
        super().paint(painter, option, index)

    def helpEvent(self, event, view, option, index):
        if index.data(Qt.ItemDataRole.ToolTipRole) == LOCKED_HINT:
            QToolTip.showText(event.globalPos(), LOCKED_HINT, view)
            return True
        return super().helpEvent(event, view, option, index)


def resolve_base_key(module_keys, installed=None):
    return installed if installed in BLUEPRINTS else DEFAULT_BLUEPRINT


def incompatible_module(module_keys, installed=None):
    base = BLUEPRINTS[resolve_base_key(module_keys, installed)]
    limit = base.tier + MAX_TIER_OFFSET
    for key in module_keys:
        module = MODULES[key]
        if module.tier > limit:
            return module, base, limit
    return None


def compatibility_error(module, base, limit):
    return 'Модуль %s (Tier %d) несовместим с корпусом %s (Tier %d). Максимальный доступный тир модулей: %d' % (
        module.name,
        module.tier,
        base.name,
        base.tier,
        limit,
    )


def build_from_keys(module_keys, installed=None):
    conflict = incompatible_module(module_keys, installed)
    if conflict is not None:
        raise ValueError(compatibility_error(*conflict))
    return assemble(BUILD_NAME, module_keys, resolve_base_key(module_keys, installed))


class ShipyardWindow(QWidget):
    back_requested = Signal()

    def __init__(self, state, settings=None, parent=None, chernobyl_active=False):
        super().__init__(parent)
        self.state = state
        self.settings = settings
        self.chernobyl_active = chernobyl_active
        self._combos = {}
        self._wear_labels = {}
        self.audio = AudioEngine(self)
        self.wear = WearState.load(os.path.join(SETTINGS_DIR, WEAR_FILENAME))
        self.setWindowTitle('РЕАКТОР — верфь')
        self.resize(1100, 700)
        self.setStyleSheet(MENU_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(_header_frame('ВЕРФЬ', 'СБОРКА РЕАКТОРА ИЗ МОДУЛЕЙ'))

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_slots(), 3)
        body.addWidget(self._build_center(), 2)
        body.addWidget(self._build_stats(), 3)
        holder = QWidget()
        holder.setLayout(body)
        root.addWidget(holder, 1)

        back = QPushButton('НАЗАД')
        back.setObjectName('menuButtonSmall')
        back.clicked.connect(lambda: self.audio.play_click())
        back.clicked.connect(self.back_requested.emit)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(back)
        back_holder = QWidget()
        back_holder.setLayout(row)
        root.addWidget(back_holder)

        mark = QLabel('@Sners1')
        mark.setStyleSheet('color: rgba(170, 140, 255, 90); font-size: 10px; letter-spacing: 1px;')
        mark_row = QHBoxLayout()
        mark_row.setContentsMargins(0, 0, 0, 0)
        mark_row.addStretch(1)
        mark_row.addWidget(mark)
        root.addLayout(mark_row)

        self.refresh()

    def closeEvent(self, event):
        self.audio.stop()
        super().closeEvent(event)

    def _build_slots(self):
        frame = QFrame()
        frame.setObjectName('menuFrame')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title = QLabel('МОДУЛИ')
        title.setObjectName('sectionTitle')
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        for row, slot in enumerate(SLOTS):
            label = QLabel(SLOT_NAMES.get(slot, slot.upper()))
            label.setObjectName('sectionHint')
            combo = QComboBox()
            combo.setItemDelegate(ModuleItemDelegate(combo))
            combo.view().setMouseTracking(True)
            combo.currentIndexChanged.connect(self._on_selection_changed)
            self._combos[slot] = combo
            wear = QLabel('')
            wear.setObjectName('sectionHint')
            wear.setMinimumWidth(96)
            self._wear_labels[slot] = wear
            grid.addWidget(label, row, 0)
            grid.addWidget(combo, row, 1)
            grid.addWidget(wear, row, 2)

        grid.setColumnStretch(1, 1)
        grid.setRowStretch(len(SLOTS), 1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)
        return frame

    def _build_center(self):
        frame = QFrame()
        frame.setObjectName('menuFrame')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel('СБОРКА')
        title.setObjectName('sectionTitle')
        layout.addWidget(title)

        self.cost_label = QLabel('')
        self.cost_label.setObjectName('balanceLabel')
        layout.addWidget(self.cost_label)

        self.status_label = QLabel('')
        self.status_label.setObjectName('sectionHint')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.assemble_button = QPushButton('СОБРАТЬ')
        self.assemble_button.setObjectName('primaryButton')
        self.assemble_button.clicked.connect(lambda: self.audio.play_click())
        self.assemble_button.clicked.connect(self._on_assemble)
        layout.addWidget(self.assemble_button)

        self.buy_button = QPushButton('КУПИТЬ И СОБРАТЬ')
        self.buy_button.setObjectName('menuButton')
        self.buy_button.clicked.connect(lambda: self.audio.play_click())
        self.buy_button.clicked.connect(self._on_buy_and_assemble)
        layout.addWidget(self.buy_button)

        self.install_button = QPushButton('УСТАНОВИТЬ')
        self.install_button.setObjectName('menuButton')
        self.install_button.clicked.connect(lambda: self.audio.play_click())
        self.install_button.clicked.connect(self._on_install)
        layout.addWidget(self.install_button)

        self.repair_button = QPushButton('ПОЧИНИТЬ МОДУЛИ')
        self.repair_button.setObjectName('menuButton')
        self.repair_button.clicked.connect(lambda: self.audio.play_click())
        self.repair_button.clicked.connect(self._on_repair)
        layout.addWidget(self.repair_button)

        self.repair_blocked_label = QLabel('Ремонт недоступен. Только замена')
        self.repair_blocked_label.setStyleSheet('color: #ff2d2d;')
        self.repair_blocked_label.setWordWrap(True)
        layout.addWidget(self.repair_blocked_label)

        layout.addStretch(1)
        return frame

    def _build_stats(self):
        frame = QFrame()
        frame.setObjectName('menuFrame')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title = QLabel('ХАРАКТЕРИСТИКИ')
        title.setObjectName('sectionTitle')
        layout.addWidget(title)

        self.stats_label = QLabel('')
        self.stats_label.setObjectName('sectionHint')
        self.stats_label.setWordWrap(True)
        self.stats_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.stats_label)
        layout.addStretch(1)
        return frame

    def module_limit(self):
        key = self.state.installed if self.state.installed in BLUEPRINTS else DEFAULT_BLUEPRINT
        return BLUEPRINTS[key].tier + MAX_TIER_OFFSET

    def _fill_combos(self):
        for slot in SLOTS:
            combo = self._combos[slot]
            previous = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for key in SLOT_MODULES[slot]:
                module = MODULES[key]
                if self.state.owns_module(key):
                    suffix = 'куплен'
                else:
                    suffix = format_credits(module.price) + ' кр.'
                combo.addItem('%s · T%d · %s' % (module.name, module.tier, suffix), key)
            index = combo.findData(previous) if previous else -1
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
        self._apply_limits()

    def _apply_limits(self):
        limit = self.module_limit()
        for slot in SLOTS:
            combo = self._combos[slot]
            model = combo.model()
            combo.blockSignals(True)
            for position in range(combo.count()):
                key = combo.itemData(position)
                item = model.item(position)
                allowed = MODULES[key].tier <= limit
                item.setEnabled(allowed)
                if allowed:
                    item.setData(None, Qt.ItemDataRole.ForegroundRole)
                    item.setData(None, Qt.ItemDataRole.BackgroundRole)
                    item.setToolTip('')
                else:
                    item.setData(QColor(LOCKED_TEXT), Qt.ItemDataRole.ForegroundRole)
                    item.setData(QColor(LOCKED_BG), Qt.ItemDataRole.BackgroundRole)
                    item.setToolTip(LOCKED_HINT)
            current = combo.currentIndex()
            if current < 0 or not model.item(current).isEnabled():
                for position in range(combo.count()):
                    if model.item(position).isEnabled():
                        combo.setCurrentIndex(position)
                        break
            combo.blockSignals(False)

    def selected_keys(self):
        return [self._combos[slot].currentData() for slot in SLOTS]

    def compatibility_conflict(self):
        return incompatible_module(self.selected_keys(), self.state.installed)

    def build_blueprint(self):
        return build_from_keys(self.selected_keys(), self.state.installed)

    def _missing_keys(self):
        return [key for key in self.selected_keys() if not self.state.owns_module(key)]

    def _on_selection_changed(self, *_args):
        self.refresh()

    def _on_assemble(self):
        try:
            self.build_blueprint()
        except (KeyError, ValueError) as error:
            self._set_status(str(error), ok=False)
            return
        self._set_status('Сборка корректна', ok=True)
        self.refresh()

    def _on_buy_and_assemble(self):
        conflict = self.compatibility_conflict()
        if conflict is not None:
            self._set_status(compatibility_error(*conflict), ok=False)
            return
        missing = self._missing_keys()
        if not missing:
            self._on_assemble()
            return
        total = assemble_cost(missing)
        if self.state.credits < total:
            self._set_status(
                'Не хватает %s кр.' % format_credits(total - self.state.credits), ok=False
            )
            return
        for key in missing:
            ok, message = self.state.buy_module(key, MODULES[key].price)
            if not ok:
                self._set_status(message, ok=False)
                self.refresh()
                return
        self._fill_combos()
        self._on_assemble()
        self._set_status('Модули куплены, сборка готова', ok=True)

    def _on_install(self):
        try:
            self.build_blueprint()
        except (KeyError, ValueError) as error:
            self._set_status(str(error), ok=False)
            return
        self.state.custom_build = list(self.selected_keys())
        self._set_status('Сборка сохранена на площадку', ok=True)

    def _set_status(self, text, ok=True):
        self.status_label.setStyleSheet('color: #22ff77;' if ok else 'color: #ff2d2d;')
        self.status_label.setText(text)

    def refresh(self):
        self._fill_combos()
        missing = self._missing_keys()
        total = assemble_cost(missing) if missing else 0.0
        self.cost_label.setText(
            'КРЕДИТЫ: %s · ДОКУПИТЬ: %s'
            % (format_credits(self.state.credits), format_credits(total))
        )
        conflict = self.compatibility_conflict()
        blocked = conflict is not None
        self.assemble_button.setEnabled(not blocked)
        self.buy_button.setEnabled(bool(missing) and not blocked)
        self.install_button.setEnabled(not missing and not blocked)
        allowed = self.repair_allowed()
        self.repair_button.setVisible(allowed)
        self.repair_blocked_label.setVisible(not allowed)
        if allowed:
            self.repair_button.setEnabled(self.state.credits >= self.repair_price())
        self._update_wear_labels()
        if blocked:
            self._set_status(compatibility_error(*conflict), ok=False)
        self._update_stats()

    def _update_stats(self):
        try:
            blueprint = self.build_blueprint()
        except (KeyError, ValueError) as error:
            self.stats_label.setStyleSheet('color: #ff2d2d;')
            self.stats_label.setText('Сборка невозможна: %s' % error)
            return
        ready, gain = compare_with_ready(blueprint)
        lines = [
            'Мощность (номинал): %.1f МВт' % blueprint.rated_power,
            'Мощность (макс): %.1f МВт' % blueprint.max_power,
            'КПД: %.3f' % blueprint.efficiency,
            'Лимит температуры: %.0f °C' % blueprint.temp_limit,
            'Лимит давления: %.2f МПа' % blueprint.pressure_limit,
            'Вес стержней: %.4f' % blueprint.rod_worth,
            'Стоимость сборки: %s кр.' % format_credits(blueprint.build_cost),
            '',
            'БЛИЖАЙШИЙ ГОТОВЫЙ: %s' % ready.name,
            'Мощность: %.1f МВт · КПД: %.3f' % (ready.rated_power, ready.efficiency),
            'Отклонение эффективности: %+.1f%%' % (gain * 100.0),
        ]
        self.stats_label.setStyleSheet('color: #22ff77;' if gain >= 0.0 else 'color: #ffcc44;')
        self.stats_label.setText('\n'.join(lines))

    # ------------------------------------------------------------ износ

    def repair_allowed(self):
        if getattr(self, 'chernobyl_active', False):
            return False
        level = getattr(self.settings, 'realism', RealismLevel.NORMAL)
        return level in (RealismLevel.ARCADE, RealismLevel.NORMAL)

    def _broken_slots(self):
        return [
            slot
            for slot in SLOTS
            if slot in self.wear.broken or self.wear.wear_of(slot) <= 0.0
        ]

    def repair_price(self):
        total = 0.0
        for slot in self._broken_slots():
            combo = self._combos.get(slot)
            key = combo.currentData() if combo is not None else None
            if key in MODULES:
                total += MODULES[key].price
        return total * 0.15

    def _on_repair(self):
        if not self.repair_allowed():
            return
        broken = self._broken_slots()
        if not broken:
            self._set_status('Все модули в порядке', ok=True)
            return
        price = self.repair_price()
        if self.state.credits < price:
            self._set_status(
                'Не хватает %s кр.' % format_credits(price - self.state.credits), ok=False
            )
            return
        self.state.credits -= price
        for slot in broken:
            self.wear.repair(slot)
        self.wear.save()
        self._set_status(
            'Модули отремонтированы: -%s кр.' % format_credits(price), ok=True
        )
        self.refresh()

    def _update_wear_labels(self):
        for slot, label in self._wear_labels.items():
            value = self.wear.wear_of(slot)
            if slot in self.wear.broken or value <= 0.0:
                label.setStyleSheet('color: #ff2d2d;')
                label.setText('СЛОМАН')
            elif value < 0.5:
                label.setStyleSheet('color: #ffcc44;')
                label.setText('Прочность: %d%%' % round(value * 100))
            else:
                label.setStyleSheet('color: #22ff77;')
                label.setText('Прочность: %d%%' % round(value * 100))
