import os
import zlib

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from economy import format_credits
from events import RandomEventManager
from about import AboutWindow
from guide import GuideWindow
from history import HistoryWindow
from menu import MainMenuWindow, SettingsWindow
from modules import assemble, resolve_modules
from reactor_core import BLUEPRINTS, RealismLevel, Reactor, create_reactor
from shipyard import ShipyardWindow, build_from_keys
from shop import ShopWindow
from settings import GameSettings
from storage import SaveManager
from ui import COLOR_ALARM, COLOR_OK, COLOR_WARN, ReactorControlWindow
from wear_state import WearState


AUTOSAVE_TICKS = 30
WEAR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wear.json')


class AppController(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = GameSettings()
        self.menu = None
        self.settings_window = None
        self.shipyard_window = None
        self.shop_window = None
        self.guide_window = None
        self.history_window = None
        self.about_window = None
        self.game = None
        self.events = None
        self.saves = SaveManager()
        self.state, error = self.saves.load()
        self.load_error = error
        self.ticks_since_save = 0
        self.wear = WearState.load(WEAR_PATH)
        self.chernobyl_active = False
        self._realism_before_scenario = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self.show_menu()

    def show_menu(self):
        if self.game is not None:
            self.saves.save(self.state)
            self._save_wear()
        self._close_game()
        self._close_settings()
        if self.menu is None:
            self.menu = MainMenuWindow(self.settings, self.state, self.load_error)
            self.menu.new_game_requested.connect(self.start_game)
            self.menu.chernobyl_requested.connect(self.start_chernobyl_game)
            self.menu.shipyard_requested.connect(self.show_shipyard)
            self.menu.shop_requested.connect(self.show_shop)
            self.menu.guide_requested.connect(self.show_guide)
            self.menu.history_requested.connect(self.show_history)
            self.menu.about_requested.connect(self.show_about)
            self.menu.settings_requested.connect(self.show_settings)
            self.menu.quit_requested.connect(self.quit)
        self.menu.set_state(self.state, self.load_error)
        self.menu.refresh_realism()
        self.menu.show()
        self.menu.raise_()
        self.menu.activateWindow()

    def show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.settings)
            self.settings_window.back_requested.connect(self._back_from_settings)
        if self.menu is not None:
            self.menu.hide()
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def show_shipyard(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.hide()
        if self.shipyard_window is None:
            self.shipyard_window = ShipyardWindow(self.state, self.settings, chernobyl_active=self.chernobyl_active)
            self.shipyard_window.back_requested.connect(self._back_from_shipyard)
        self.shipyard_window.refresh()
        self.shipyard_window.show()
        self.shipyard_window.raise_()
        self.shipyard_window.activateWindow()

    def show_shop(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.hide()
        if self.shop_window is None:
            self.shop_window = ShopWindow(self.state)
            self.shop_window.back_requested.connect(self._back_from_shop)
        self.shop_window.refresh()
        self.shop_window.show()
        self.shop_window.raise_()
        self.shop_window.activateWindow()

    def show_guide(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.hide()
        if self.guide_window is None:
            self.guide_window = GuideWindow()
            self.guide_window.back_requested.connect(self._back_from_guide)
        self.guide_window.show()
        self.guide_window.raise_()
        self.guide_window.activateWindow()

    def _close_guide(self):
        window = self.guide_window
        self.guide_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def _back_from_guide(self):
        self._close_guide()
        if self.menu is not None:
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def show_history(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.hide()
        if self.history_window is None:
            self.history_window = HistoryWindow()
            self.history_window.back_requested.connect(self._back_from_history)
        self.history_window.show()
        self.history_window.raise_()
        self.history_window.activateWindow()

    def _close_history(self):
        window = self.history_window
        self.history_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def _back_from_history(self):
        self._close_history()
        if self.menu is not None:
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def show_about(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.hide()
        if self.about_window is None:
            self.about_window = AboutWindow()
            self.about_window.back_requested.connect(self._back_from_about)
        self.about_window.show()
        self.about_window.raise_()
        self.about_window.activateWindow()

    def _close_about(self):
        window = self.about_window
        self.about_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def _back_from_about(self):
        self._close_about()
        if self.menu is not None:
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def _close_shop(self):
        window = self.shop_window
        self.shop_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def _back_from_shop(self):
        self._close_shop()
        if self.menu is not None:
            self.menu.set_state(self.state, self.load_error)
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def _close_shipyard(self):
        window = self.shipyard_window
        self.shipyard_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def _back_from_shipyard(self):
        self._close_shipyard()
        if self.menu is not None:
            self.menu.set_state(self.state, self.load_error)
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def _back_from_settings(self):
        self._close_settings()
        if self.menu is not None:
            self.menu.refresh_realism()
            self.menu.show()
            self.menu.raise_()
            self.menu.activateWindow()

    def start_chernobyl_game(self):
        self._apply_hardcore()
        self.start_game()
        self.chernobyl_active = True
        if self.events is not None:
            self.events.start_chernobyl()

    def _apply_hardcore(self):
        previous = getattr(self.settings, 'realism', None)
        if self._realism_before_scenario is None:
            self._realism_before_scenario = previous
        self._set_realism(RealismLevel.HARDCORE)
        if self.menu is not None:
            self.menu.refresh_realism()

    def _restore_realism(self):
        previous = self._realism_before_scenario
        if previous is None:
            return
        self._realism_before_scenario = None
        self._set_realism(previous)
        if self.menu is not None:
            self.menu.refresh_realism()

    def _set_realism(self, level):
        try:
            ok, _error = self.settings.set_realism(level)
        except Exception:
            ok = False
        if not ok:
            self.settings._realism = level

    def start_game(self):
        self._close_settings()
        self.chernobyl_active = False
        if self.menu is not None:
            self.menu.hide()

        if self.state.custom_build:
            blueprint = build_from_keys(self.state.custom_build, self.state.installed)
            reactor = Reactor(blueprint, self.settings.realism)
        else:
            reactor = create_reactor(self.state.installed, realism=self.settings.realism)
        self.wear = WearState.load(WEAR_PATH)
        self.wear.apply(reactor, self._install_token())
        game = ReactorControlWindow(reactor)
        self.events = RandomEventManager(reactor)
        self.events.logger = lambda message: game._log(message, COLOR_ALARM)
        self.chernobyl_shortcut = QShortcut(QKeySequence("F9"), game)
        self.chernobyl_shortcut.activated.connect(self._toggle_chernobyl)
        game.pause_toggled.connect(self._on_pause_toggled)
        game.menu_requested.connect(self.show_menu)
        game.destroyed.connect(self._on_game_destroyed)
        self.game = game
        game.show()
        game.raise_()
        game.activateWindow()
        self.timer.start()

    def _tick(self):
        game = self.game
        if game is None or game.paused:
            return
        if self.events is not None:
            self.events.update(1.0)
        game.reactor.step(1.0)
        self._sync_wear(game)
        events = self.state.tick(1.0, game.reactor.electrical_power_mw)
        earned = events.get('earned')
        if earned:
            game._log('Начислено %s кр. за выработку' % format_credits(earned), COLOR_OK)
        completed = events.get('completed')
        if completed:
            game._log('Сборка завершена: «%s» выведен на площадку' % BLUEPRINTS[completed].name, COLOR_WARN)
        self.ticks_since_save += 1
        if self.ticks_since_save >= AUTOSAVE_TICKS:
            self.ticks_since_save = 0
            self.saves.save(self.state)
            self._save_wear()
        game.update_ui()

    def _install_token(self):
        key = repr((self.state.custom_build, self.state.installed))
        return zlib.crc32(key.encode('utf-8'))

    def _sync_wear(self, game):
        for message in game.reactor.drain_wear_messages():
            game._log(message, COLOR_ALARM)
        if self.wear is not None:
            self.wear.capture(game.reactor, self._install_token())

    def _save_wear(self):
        if self.wear is None:
            return
        game = self.game
        if game is not None:
            self.wear.capture(game.reactor, self._install_token())
        self.wear.save()

    def _toggle_chernobyl(self):
        events = self.events
        if events is None:
            return
        if events.scenario:
            events.stop_chernobyl()
        else:
            events.start_chernobyl()

    def _on_pause_toggled(self, paused):
        if paused:
            self.timer.stop()
        elif self.game is not None:
            self.timer.start()

    def _on_game_destroyed(self, *_args):
        self.timer.stop()
        self._save_wear()
        self.game = None
        self.events = None
        self._end_chernobyl_if_active()

    def _end_chernobyl_if_active(self):
        if not self.chernobyl_active:
            return
        self.chernobyl_active = False
        self._restore_realism()

    def _close_game(self):
        self.timer.stop()
        game = self.game
        self.game = None
        self._end_chernobyl_if_active()
        if game is not None:
            game.close()
            game.deleteLater()

    def _close_settings(self):
        window = self.settings_window
        self.settings_window = None
        if window is not None:
            window.close()
            window.deleteLater()

    def quit(self):
        self.timer.stop()
        self.saves.save(self.state)
        self._save_wear()
        self._close_game()
        self._close_settings()
        if self.menu is not None:
            self.menu.close()
            self.menu.deleteLater()
            self.menu = None
        self.app.quit()
