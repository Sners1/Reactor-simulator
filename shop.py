from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from audio import AudioEngine
from economy import CATALOG, ORDER, GameState, format_credits, format_duration
from menu import MENU_QSS, _header_frame
from reactor_core import BLUEPRINTS


SHOP_ORDER = tuple(key for key in ORDER if key in BLUEPRINTS)


class ShopWindow(QWidget):
    back_requested = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._cards = {}
        self.audio = AudioEngine(self)
        self.setWindowTitle('РЕАКТОР — магазин чертежей')
        self.resize(1100, 760)
        self.setStyleSheet(MENU_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(_header_frame('МАГАЗИН ЧЕРТЕЖЕЙ', 'ПРОЕКТЫ ЭНЕРГОБЛОКОВ ОТ БАЗОВОГО ДО НЕВОЗМОЖНОГО'))

        self.credits_label = QLabel('')
        self.credits_label.setObjectName('balanceLabel')
        root.addWidget(self.credits_label)

        self.status_label = QLabel('')
        self.status_label.setObjectName('sectionHint')
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        root.addWidget(self._build_list(), 1)

        back = QPushButton('НАЗАД')
        back.setObjectName('menuButtonSmall')
        back.clicked.connect(lambda: self.audio.play_click())
        back.clicked.connect(self.back_requested.emit)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(back)
        holder = QWidget()
        holder.setLayout(row)
        root.addWidget(holder)

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

    def _build_list(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for key in SHOP_ORDER:
            layout.addWidget(self._make_card(key))
        layout.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def _make_card(self, key):
        blueprint = BLUEPRINTS[key]
        entry = CATALOG[key]

        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        name = QLabel(blueprint.name.upper())
        name.setObjectName('shopName')
        tier = QLabel('TIER %d · СЛОЖНОСТЬ %.0f%%' % (blueprint.tier, blueprint.difficulty * 100.0))
        tier.setObjectName('shopTier')
        head.addWidget(name)
        head.addStretch(1)
        head.addWidget(tier)
        layout.addLayout(head)

        tagline = QLabel(entry.tagline)
        tagline.setObjectName('shopTagline')
        layout.addWidget(tagline)

        desc = QLabel(entry.description)
        desc.setObjectName('shopDesc')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        stats = QLabel(
            'Мощность: %.1f МВт (макс %.1f) · КПД: %.3f\n'
            'Температура: %.0f °C · Давление: %.1f МПа\n'
            'Доход: %s кр./ч · Сборка: %s'
            % (
                blueprint.rated_power,
                blueprint.max_power,
                blueprint.efficiency,
                blueprint.temp_limit,
                blueprint.pressure_limit,
                format_credits(GameState.income_rate(key)),
                format_duration(self.state.build_time(key)),
            )
        )
        stats.setObjectName('shopStats')
        layout.addWidget(stats)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 6, 0, 0)
        price = QLabel('')
        price.setObjectName('shopPrice')
        button = QPushButton('')
        button.setObjectName('menuButtonSmall')
        button.clicked.connect(lambda: self.audio.play_click())
        button.clicked.connect(lambda _checked=False, k=key: self._on_action(k))
        bottom.addWidget(price)
        bottom.addStretch(1)
        bottom.addWidget(button)
        layout.addLayout(bottom)

        self._cards[key] = (frame, price, button)
        return frame

    def _set_status(self, text, ok=True):
        self.status_label.setStyleSheet('color: #22ff77;' if ok else 'color: #ffcc44;')
        self.status_label.setText(text)

    def _refresh_card(self, key):
        frame, price, button = self._cards[key]
        blueprint = BLUEPRINTS[key]
        owned = self.state.owns(key)
        installed = self.state.installed == key
        frame.setObjectName('shopCardOwned' if owned else 'shopCard')
        frame.style().unpolish(frame)
        frame.style().polish(frame)

        price.setText('ЦЕНА: %s кр.' % format_credits(self.state.price(key)))
        button.setEnabled(False)
        button.setToolTip('')

        if owned:
            if installed:
                button.setText('УСТАНОВЛЕН')
                button.setToolTip('Этот энергоблок уже стоит на площадке')
            else:
                button.setText('УСТАНОВИТЬ')
                button.setEnabled(True)
                button.setToolTip('Вывести «%s» на площадку' % blueprint.name)
            return

        button.setText('КУПИТЬ')
        if not self.state.is_unlocked(key):
            requires = CATALOG[key].requires
            required_name = BLUEPRINTS[requires].name if requires in BLUEPRINTS else 'предыдущий'
            button.setToolTip('Сначала нужен чертёж «%s»' % required_name)
            return
        if self.state.build_key:
            button.setToolTip(
                'Верфь занята: достраивается «%s»'
                % BLUEPRINTS[self.state.build_key].name
            )
            return
        cost = self.state.price(key)
        if self.state.credits < cost:
            button.setToolTip(
                'Не хватает %s кр.' % format_credits(cost - self.state.credits)
            )
            return
        button.setEnabled(True)
        button.setToolTip('Купить чертёж и заложить энергоблок')

    def refresh(self):
        self.credits_label.setText('КРЕДИТЫ: %s' % format_credits(self.state.credits))
        for key in SHOP_ORDER:
            self._refresh_card(key)

    def _on_action(self, key):
        if self.state.owns(key):
            ok, message = self.state.install(key)
        else:
            ok, message = self.state.purchase(key)
        self._set_status(message, ok=ok)
        self.refresh()
