import math
from dataclasses import dataclass
from typing import Optional

from modules import MODULES, resolve_modules
from reactor_core import BLUEPRINTS


CREDITS_PER_MWH = 7200.0
# build_time в BLUEPRINTS задан в секундах: 60 / 900 / 7200 / 86400 / 604800.
# При BUILD_SPEED = 100 «Невозможный» собирался бы 100 минут, что ломает
# требование «build_time не больше 2-3 минут», поэтому ускорение 4000x:
# 0.015 / 0.225 / 1.8 / 21.6 / 151.2 секунд.
BUILD_SPEED = 4000.0
# Тира 1-4 подобраны так, что каждый переход занимает ~14 минут:
# farm = price(next) / (rated_power * profit * 2), где 7200/3600 = 2.
# Тир 5: rated_power в 20.8 раза выше, чем у 4-го, поэтому profit=520 даёт
# 9.36e12 кр/ч (> 8.64e12 у 4-го, монотонно) и ~10 минут на кастомный чертёж.
# profit=9600 дал бы ровно 20x роста, но кастомный чертёж фармился бы 42 секунды.
TIER_PROFIT = {1: 15.0, 2: 48.0, 3: 600.0, 4: 10000.0, 5: 520.0}
DEFAULT_BLUEPRINT = 'base'
SAVE_VERSION = 2


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    tagline: str
    description: str
    requires: Optional[str] = None


CATALOG = {
    'base': CatalogEntry(
        'base',
        'Графит, вода и оптимизм',
        'Классика жанра: чугунный купол, графитовая кладка и уверенность, что всё под контролем. Первый шаг от лопаты к энергетике.',
    ),
    'medium': CatalogEntry(
        'medium',
        'Промышленный сердечник',
        'Парогенератор «Самовар» кипит ровно, приводы стержней щёлкают в такт. Уже не игрушка, но ещё не легенда.',
        requires='base',
    ),
    'high': CatalogEntry(
        'high',
        'Тяжёлый энергоблок',
        'Многоконтурная схема и борный узел «Кислота». Для тех, кто любит большие цифры в счётчике и маленькие — в допусках.',
        requires='medium',
    ),
    'extreme': CatalogEntry(
        'extreme',
        'Плутоний и натрий',
        'Жидкометаллический теплоноситель и каскад турбин «Вихрь». Один неверный стержень — и объект станет местной достопримечательностью.',
        requires='high',
    ),
    'impossible': CatalogEntry(
        'impossible',
        'Физика подаёт апелляцию',
        'Тороидальное ядро «Кольцо», сверхпроводящие магниты «Иней» и квантовая защита «Наблюдатель». Прибыль, от которой плавятся предохранители, и счёт за металл, от которого плавится бухгалтерия.',
        requires='extreme',
    ),
    'custom': CatalogEntry(
        'custom',
        'Авторский чертёж',
        'Ваши пропорции, ваша подпись, ваша ответственность. Собирается из лучших узлов «Невозможного», но с вашими личными странностями.',
        requires='impossible',
    ),
}

ORDER = ('base', 'medium', 'high', 'extreme', 'impossible', 'custom')


class GameState:
    def __init__(
        self,
        credits=0.0,
        purchased=None,
        installed=DEFAULT_BLUEPRINT,
        build_key=None,
        build_remaining=0.0,
        total_earned=0.0,
        total_spent=0.0,
        install_token=0,
        owned_modules=None,
        custom_build=None,
    ):
        self.credits = float(credits)
        self.purchased = set(purchased or ())
        self.purchased.add(DEFAULT_BLUEPRINT)
        self.installed = installed if installed in self.purchased else DEFAULT_BLUEPRINT
        self.build_key = build_key if build_key in BLUEPRINTS else None
        self.build_remaining = float(build_remaining) if self.build_key else 0.0
        self.total_earned = float(total_earned)
        self.total_spent = float(total_spent)
        self.install_token = int(install_token)
        self.owned_modules = {key for key in (owned_modules or ()) if key in MODULES}
        self.custom_build = self._clean_build(custom_build)

    @staticmethod
    def _clean_build(custom_build):
        if not custom_build:
            return None
        keys = [key for key in custom_build if key in MODULES]
        try:
            resolve_modules(keys)
        except (KeyError, ValueError):
            return None
        return keys

    @property
    def blueprint(self):
        return BLUEPRINTS[self.installed]

    @property
    def profit_multiplier(self):
        return TIER_PROFIT.get(self.blueprint.tier, 1.0)

    def owns(self, key):
        return key in self.purchased

    def owns_module(self, key):
        return key in self.owned_modules

    def buy_module(self, key, price=None):
        if key not in MODULES:
            return False, 'Неизвестный модуль'
        if self.owns_module(key):
            return True, 'Модуль «%s» уже куплен' % MODULES[key].name
        cost = MODULES[key].price if price is None else float(price)
        if self.credits < cost:
            return False, 'Не хватает кредитов: нужно %s' % format_credits(cost)
        self.credits -= cost
        self.total_spent += cost
        self.owned_modules.add(key)
        return True, 'Куплен модуль «%s»' % MODULES[key].name

    def price(self, key):
        return BLUEPRINTS[key].build_cost

    def build_time(self, key):
        return BLUEPRINTS[key].build_time / BUILD_SPEED

    @staticmethod
    def income_rate(key):
        blueprint = BLUEPRINTS[key]
        profit = TIER_PROFIT.get(blueprint.tier, 1.0)
        return blueprint.rated_power * profit * CREDITS_PER_MWH / 3600.0

    def is_unlocked(self, key):
        entry = CATALOG.get(key)
        if entry is None:
            return False
        if entry.requires is None:
            return True
        return self.owns(entry.requires)

    def purchase(self, key):
        if key not in BLUEPRINTS or key not in CATALOG:
            return False, 'Неизвестный чертёж'
        if self.owns(key):
            return self.install(key)
        if not self.is_unlocked(key):
            entry = CATALOG[key]
            return False, 'Сначала нужен чертёж «%s»' % BLUEPRINTS[entry.requires].name
        if self.build_key:
            return False, 'Верфь занята: достраивается «%s»' % BLUEPRINTS[self.build_key].name
        cost = self.price(key)
        if self.credits < cost:
            return False, 'Не хватает %s кр.' % format_credits(cost - self.credits)
        self.credits -= cost
        self.total_spent += cost
        self.build_key = key
        self.build_remaining = self.build_time(key)
        return True, 'Заложен энергоблок «%s»: сборка %s' % (
            BLUEPRINTS[key].name,
            format_duration(self.build_remaining),
        )

    def install(self, key):
        if key not in BLUEPRINTS:
            return False, 'Неизвестный чертёж'
        if not self.owns(key):
            return False, 'Чертёж «%s» не приобретён' % BLUEPRINTS[key].name
        self.installed = key
        self.install_token += 1
        return True, 'Энергоблок «%s» выведен на площадку' % BLUEPRINTS[key].name

    def tick(self, dt, electrical_mw):
        events = {}
        if dt <= 0.0:
            return events
        if electrical_mw > 0.0:
            earned = electrical_mw * dt / 3600.0 * CREDITS_PER_MWH * self.profit_multiplier
            self.credits += earned
            self.total_earned += earned
            events['earned'] = earned
        if self.build_key:
            self.build_remaining -= dt
            if self.build_remaining <= 0.0:
                finished = self.build_key
                self.build_key = None
                self.build_remaining = 0.0
                self.purchased.add(finished)
                self.installed = finished
                self.install_token += 1
                events['completed'] = finished
        return events

    def to_dict(self):
        return {
            'version': SAVE_VERSION,
            'credits': round(self.credits, 3),
            'purchased': sorted(self.purchased),
            'installed': self.installed,
            'build_key': self.build_key,
            'build_remaining': round(self.build_remaining, 3),
            'total_earned': round(self.total_earned, 3),
            'total_spent': round(self.total_spent, 3),
            'install_token': self.install_token,
            'owned_modules': sorted(self.owned_modules),
            'custom_build': list(self.custom_build) if self.custom_build else None,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise TypeError('save data must be a dict')
        purchased = [key for key in data.get('purchased', ()) if key in BLUEPRINTS]
        return cls(
            credits=float(data.get('credits', 0.0)),
            purchased=purchased,
            installed=str(data.get('installed', DEFAULT_BLUEPRINT)),
            build_key=data.get('build_key'),
            build_remaining=float(data.get('build_remaining', 0.0)),
            total_earned=float(data.get('total_earned', 0.0)),
            total_spent=float(data.get('total_spent', 0.0)),
            install_token=int(data.get('install_token', 0)),
            owned_modules=data.get('owned_modules'),
            custom_build=data.get('custom_build'),
        )


def format_credits(value):
    value = max(0.0, float(value))
    if value >= 1.0e12:
        return '%.2f трлн' % (value / 1.0e12)
    if value >= 1.0e9:
        return '%.2f млрд' % (value / 1.0e9)
    if value >= 1.0e6:
        return '%.2f млн' % (value / 1.0e6)
    if value >= 1.0e5:
        return '{:,.0f}'.format(value).replace(',', ' ')
    return '{:,.1f}'.format(value).replace(',', ' ')


def format_duration(seconds):
    total = int(max(0.0, math.ceil(seconds)))
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return '%d д %02d:%02d:%02d' % (days, hours, minutes, secs)
    return '%02d:%02d:%02d' % (hours, minutes, secs)
