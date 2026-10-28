import json
import os
import tempfile

from reactor_core import RealismLevel


SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

REALISM_ORDER = (RealismLevel.ARCADE, RealismLevel.NORMAL, RealismLevel.HARDCORE)

REALISM_NAMES = {
    RealismLevel.ARCADE: 'Аркада',
    RealismLevel.NORMAL: 'Нормал',
    RealismLevel.HARDCORE: 'Хардкор',
}

REALISM_DESCRIPTIONS = {
    RealismLevel.ARCADE: (
        'Прощает ошибки: медленные отклики, мягкие обратные связи, '
        'повышенные пределы и длительная пауза перед отказом.'
    ),
    RealismLevel.NORMAL: 'Сбалансированный режим: базовая физика без поблажек.',
    RealismLevel.HARDCORE: (
        'Жёсткая физика: усиленные обратные связи по ксенону и пустотам, '
        'сниженные пределы, отказы без периода прощения.'
    ),
}

DEFAULT_REALISM = RealismLevel.NORMAL


def _coerce_level(raw):
    if isinstance(raw, RealismLevel):
        return raw
    text = str(raw or '').strip().lower()
    for level in REALISM_ORDER:
        if level.value == text:
            return level
    return DEFAULT_REALISM


class GameSettings:
    def __init__(self, path=SETTINGS_FILE):
        self.path = path
        self._realism = DEFAULT_REALISM
        self.load()

    @property
    def realism(self):
        return self._realism

    def load(self):
        self._realism = DEFAULT_REALISM
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
        except (OSError, ValueError, TypeError):
            return
        if isinstance(raw, dict):
            self._realism = _coerce_level(raw.get('realism'))

    def set_realism(self, level):
        level = _coerce_level(level)
        previous = self._realism
        self._realism = level
        ok, error = self.save()
        if not ok:
            self._realism = previous
            return False, error
        return True, None

    def save(self):
        directory = os.path.dirname(self.path) or '.'
        try:
            os.makedirs(directory, exist_ok=True)
            payload = json.dumps(
                {'realism': self._realism.value}, ensure_ascii=False, indent=2
            )
            handle = tempfile.NamedTemporaryFile(
                'w', encoding='utf-8', dir=directory, delete=False, suffix='.tmp'
            )
            with handle:
                handle.write(payload)
            os.replace(handle.name, self.path)
        except OSError as error:
            try:
                os.unlink(handle.name)
            except (OSError, NameError):
                pass
            return False, 'Не удалось сохранить настройки: %s' % error
        return True, None
