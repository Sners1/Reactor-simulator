"""Хранение износа модулей между запусками игры.

Износ считается в Reactor (reactor_core), но переживает перезапуск:
WearState копирует значения из реактора при остановке игры и возвращает
их обратно при следующем запуске. Износ привязан к install_token —
после установки новой сборки все модули считаются новыми.
"""

import json
import os
import tempfile

from reactor_core import WEAR_SLOTS


WEAR_FILENAME = 'wear.json'
REPAIR_SHARE = 0.45
REPAIR_MIN = 250.0
BROKEN_SURCHARGE = 1.25


def _clean_value(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return min(1.0, max(0.0, value))


class WearState:
    def __init__(self, path, values=None, broken=None, install_token=-1):
        self.path = path
        self.values = {slot: 1.0 for slot in WEAR_SLOTS}
        for slot, value in dict(values or {}).items():
            if slot in self.values:
                self.values[slot] = _clean_value(value)
        self.broken = {slot for slot in (broken or ()) if slot in self.values}
        self.install_token = int(install_token)

    # ------------------------------------------------------------ файл

    @classmethod
    def load(cls, path):
        state = cls(path)
        if not os.path.isfile(path):
            return state
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
        except (OSError, ValueError, TypeError):
            return state
        if not isinstance(raw, dict):
            return state
        return cls(path, raw.get('wear'), raw.get('broken'), raw.get('install_token', -1))

    def to_dict(self):
        return {
            'version': 1,
            'install_token': self.install_token,
            'wear': {slot: round(value, 4) for slot, value in self.values.items()},
            'broken': sorted(self.broken),
        }

    def save(self):
        directory = os.path.dirname(self.path) or '.'
        try:
            os.makedirs(directory, exist_ok=True)
            payload = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
            handle = tempfile.NamedTemporaryFile(
                'w', encoding='utf-8', dir=directory, delete=False, suffix='.tmp'
            )
        except OSError:
            return False
        try:
            with handle:
                handle.write(payload)
            os.replace(handle.name, self.path)
        except OSError:
            try:
                os.unlink(handle.name)
            except OSError:
                pass
            return False
        return True

    # --------------------------------------------------------- реактор

    def reset(self):
        self.values = {slot: 1.0 for slot in WEAR_SLOTS}
        self.broken = set()

    def capture(self, reactor, install_token):
        self.install_token = int(install_token)
        for slot in WEAR_SLOTS:
            self.values[slot] = _clean_value(reactor.wear.get(slot, 1.0))
        self.broken = {slot for slot in reactor.broken if slot in self.values}

    def apply(self, reactor, install_token):
        token = int(install_token)
        if token != self.install_token:
            self.install_token = token
            self.reset()
        reactor.wear = {slot: self.values.get(slot, 1.0) for slot in WEAR_SLOTS}
        reactor.broken = set(self.broken)
        for slot in self.broken:
            reactor.wear[slot] = 0.0
        return True

    # ---------------------------------------------------------- ремонт

    def wear_of(self, slot):
        return self.values.get(slot, 1.0)

    def is_broken(self, slot):
        return slot in self.broken

    def needs_repair(self, slot):
        return slot in self.broken or self.values.get(slot, 1.0) < 0.999

    def repair_cost(self, slot, price):
        if not self.needs_repair(slot):
            return 0.0
        price = max(0.0, float(price))
        if slot in self.broken:
            cost = price * REPAIR_SHARE * BROKEN_SURCHARGE
        else:
            cost = price * REPAIR_SHARE * (1.0 - self.values.get(slot, 1.0))
        return max(REPAIR_MIN, cost)

    def total_repair_cost(self, prices):
        return sum(self.repair_cost(slot, prices.get(slot, 0.0)) for slot in WEAR_SLOTS)

    def repair(self, slot):
        if slot not in self.values:
            return False
        self.values[slot] = 1.0
        self.broken.discard(slot)
        return True

    def repair_all(self):
        for slot in WEAR_SLOTS:
            self.repair(slot)
