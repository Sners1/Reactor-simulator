import json
import os
import tempfile

from economy import GameState


SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
SAVE_FILE = os.path.join(SAVE_DIR, 'progress.json')


class SaveManager:
    def __init__(self, path=SAVE_FILE):
        self.path = path

    def exists(self):
        return os.path.isfile(self.path)

    def load(self):
        if not self.exists():
            return GameState(), None
        try:
            with open(self.path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
            return GameState.from_dict(raw), None
        except (OSError, ValueError, TypeError) as error:
            return GameState(), 'Сохранение повреждено (%s) — начат новый профиль' % error

    def save(self, state):
        directory = os.path.dirname(self.path) or '.'
        os.makedirs(directory, exist_ok=True)
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        handle = tempfile.NamedTemporaryFile(
            'w', encoding='utf-8', dir=directory, delete=False, suffix='.tmp'
        )
        try:
            with handle:
                handle.write(payload)
            os.replace(handle.name, self.path)
            return True, None
        except OSError as error:
            try:
                os.unlink(handle.name)
            except OSError:
                pass
            return False, 'Не удалось записать сохранение: %s' % error

    def reset(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        except OSError as error:
            return False, str(error)
        return True, None
