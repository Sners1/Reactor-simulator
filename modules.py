from dataclasses import dataclass, replace
from typing import Dict, Tuple

from reactor_core import BLUEPRINTS, P_NOMINAL, T_REFERENCE, Blueprint


SLOTS = ('hull', 'fuel', 'rods', 'pump', 'turbine', 'shield')

TIER_PRICE = {1: 8.0, 2: 27.0, 3: 92.0, 4: 313.0, 5: 1064.0}

MODIFIER_FIELDS = (
    'rated_power',
    'max_power',
    'efficiency',
    'temp_limit',
    'pressure_limit',
    'rod_worth',
    'temp_coefficient',
    'void_coefficient',
    'xenon_worth',
    'xenon_yield',
)

MAX_TIER_OFFSET = 1
BUILD_TIME_DURABILITY = 1.0


@dataclass(frozen=True)
class Module:
    key: str
    slot: str
    name: str
    tier: int
    price: float
    durability: float
    rated_power: float = 1.0
    max_power: float = 1.0
    efficiency: float = 1.0
    temp_limit: float = 1.0
    pressure_limit: float = 1.0
    rod_worth: float = 1.0
    temp_coefficient: float = 1.0
    void_coefficient: float = 1.0
    xenon_worth: float = 1.0
    xenon_yield: float = 1.0

    def __post_init__(self):
        if self.slot not in SLOTS:
            raise ValueError('unknown slot: ' + str(self.slot))
        if not 1 <= self.tier <= 5:
            raise ValueError('module tier must be within 1..5')
        if self.price <= 0.0:
            raise ValueError('module price must be positive')
        if not 0.0 < self.durability <= 1.0:
            raise ValueError('module durability must be within (0, 1]')
        for field in MODIFIER_FIELDS:
            if getattr(self, field) <= 0.0:
                raise ValueError('module %s multiplier must be positive' % field)


_CATALOG = (
    ('hull_t1', 'hull', 'Клёпаный кожух «Лата»', 1, 0.70, {'temp_limit': 1.04, 'pressure_limit': 1.04}),
    ('hull_t2', 'hull', 'Литой корпус «Кувалда»', 2, 0.80, {'temp_limit': 1.07, 'pressure_limit': 1.07}),
    ('hull_t3', 'hull', 'Кованый корпус «Бастион»', 3, 0.88, {'temp_limit': 1.09, 'pressure_limit': 1.09}),
    ('hull_t4', 'hull', 'Сварной корпус «Утёс»', 4, 0.92, {'temp_limit': 1.11, 'pressure_limit': 1.11}),
    ('hull_t5', 'hull', 'Композитная скорлупа «Монолит»', 5, 0.96, {'temp_limit': 1.13, 'pressure_limit': 1.13}),

    ('fuel_t1', 'fuel', 'Топливные таблетки «Крошка»', 1, 0.70, {'rated_power': 1.030, 'xenon_yield': 0.98}),
    ('fuel_t2', 'fuel', 'Обогащённые сборки «Игла»', 2, 0.80, {'rated_power': 1.030, 'xenon_yield': 0.96}),
    ('fuel_t3', 'fuel', 'Смешанное оксидное топливо «Мозаика»', 3, 0.88, {'rated_power': 1.030, 'xenon_yield': 0.94}),
    ('fuel_t4', 'fuel', 'Уран-плутониевые кассеты «Ковчег»', 4, 0.92, {'rated_power': 1.030, 'xenon_yield': 0.92}),
    ('fuel_t5', 'fuel', 'Плутониевые капсулы «Геенна»', 5, 0.96, {'rated_power': 1.030, 'xenon_yield': 0.90}),

    ('rods_t1', 'rods', 'Стержни БШ-2 «Прутик»', 1, 0.70, {'rated_power': 1.020, 'rod_worth': 1.03, 'void_coefficient': 0.98}),
    ('rods_t2', 'rods', 'Стержни с гидроприводом «Хлыст»', 2, 0.80, {'rated_power': 1.020, 'rod_worth': 1.05, 'void_coefficient': 0.96}),
    ('rods_t3', 'rods', 'Бор-карбидные стержни «Клешня»', 3, 0.88, {'rated_power': 1.020, 'rod_worth': 1.08, 'void_coefficient': 0.94}),
    ('rods_t4', 'rods', 'Стержни с гафниевым сердечником «Клык»', 4, 0.92, {'rated_power': 1.020, 'rod_worth': 1.10, 'void_coefficient': 0.925}),
    ('rods_t5', 'rods', 'Наноуправляемые стержни «Нерв»', 5, 0.96, {'rated_power': 1.020, 'rod_worth': 1.12, 'void_coefficient': 0.91}),

    ('pump_t1', 'pump', 'Насос «Ручеёк»', 1, 0.70, {'rated_power': 1.015, 'efficiency': 1.013, 'temp_coefficient': 1.02}),
    ('pump_t2', 'pump', 'Центробежный насос «Поток»', 2, 0.80, {'rated_power': 1.015, 'efficiency': 1.014, 'temp_coefficient': 1.05}),
    ('pump_t3', 'pump', 'Главный насос «Водоворот»', 3, 0.88, {'rated_power': 1.015, 'efficiency': 1.015, 'temp_coefficient': 1.08}),
    ('pump_t4', 'pump', 'Двухскоростной насос «Прилив»', 4, 0.92, {'rated_power': 1.015, 'efficiency': 1.016, 'temp_coefficient': 1.10}),
    ('pump_t5', 'pump', 'Магнитогидродинамический насос «Пульс»', 5, 0.96, {'rated_power': 1.015, 'efficiency': 1.017, 'temp_coefficient': 1.12}),

    ('turbine_t1', 'turbine', 'Турбина «Вертушка»', 1, 0.70, {'rated_power': 1.025, 'max_power': 1.02, 'efficiency': 1.016}),
    ('turbine_t2', 'turbine', 'Турбина «Шмель»', 2, 0.80, {'rated_power': 1.025, 'max_power': 1.05, 'efficiency': 1.017}),
    ('turbine_t3', 'turbine', 'Турбина высокого давления «Сокол»', 3, 0.88, {'rated_power': 1.025, 'max_power': 1.08, 'efficiency': 1.018}),
    ('turbine_t4', 'turbine', 'Двухпоточная турбина «Гриф»', 4, 0.92, {'rated_power': 1.025, 'max_power': 1.10, 'efficiency': 1.019}),
    ('turbine_t5', 'turbine', 'Каскад «Сирена»', 5, 0.96, {'rated_power': 1.025, 'max_power': 1.13, 'efficiency': 1.020}),

    ('shield_t1', 'shield', 'Защитный экран «Фартук»', 1, 0.70, {'temp_limit': 1.03, 'pressure_limit': 1.03, 'xenon_worth': 0.97}),
    ('shield_t2', 'shield', 'Бетонная защита «Саркофаг-лайт»', 2, 0.80, {'temp_limit': 1.05, 'pressure_limit': 1.05, 'xenon_worth': 0.95}),
    ('shield_t3', 'shield', 'Многослойная защита «Панцирь»', 3, 0.88, {'temp_limit': 1.07, 'pressure_limit': 1.07, 'xenon_worth': 0.93}),
    ('shield_t4', 'shield', 'Биологическая защита «Цитадель»', 4, 0.92, {'temp_limit': 1.085, 'pressure_limit': 1.085, 'xenon_worth': 0.91}),
    ('shield_t5', 'shield', 'Квантовый контур «Наблюдатель»', 5, 0.96, {'temp_limit': 1.10, 'pressure_limit': 1.10, 'xenon_worth': 0.89}),
)


MODULES: Dict[str, Module] = {
    key: Module(key, slot, name, tier, TIER_PRICE[tier], durability, **mods)
    for key, slot, name, tier, durability, mods in _CATALOG
}

if len(MODULES) != len(_CATALOG):
    raise RuntimeError('duplicate module keys in catalog')


SLOT_MODULES: Dict[str, Tuple[str, ...]] = {
    slot: tuple(sorted(key for key, module in MODULES.items() if module.slot == slot))
    for slot in SLOTS
}


def resolve_modules(module_keys):
    filled = {}
    modules = []
    for key in module_keys:
        if key not in MODULES:
            raise KeyError('unknown module: ' + str(key))
        module = MODULES[key]
        if module.slot in filled:
            raise ValueError('slot %s already filled by %s' % (module.slot, filled[module.slot]))
        filled[module.slot] = key
        modules.append(module)
    missing = [slot for slot in SLOTS if slot not in filled]
    if missing:
        raise ValueError('empty slots: ' + ', '.join(missing))
    return tuple(modules)


def assemble_cost(module_keys) -> float:
    total = 0.0
    for key in module_keys:
        if key not in MODULES:
            raise KeyError('unknown module: ' + str(key))
        total += MODULES[key].price
    return total


def _check_bounds(values, base_key):
    problems = []
    if values['rated_power'] <= 0.0:
        problems.append('rated_power must be positive')
    if values['max_power'] < values['rated_power']:
        problems.append('max_power must not be below rated_power')
    if not 0.0 < values['efficiency'] < 1.0:
        problems.append('efficiency must be between 0 and 1')
    if values['temp_limit'] <= T_REFERENCE:
        problems.append('temp_limit must exceed reference temperature')
    if values['pressure_limit'] <= P_NOMINAL:
        problems.append('pressure_limit must exceed nominal pressure')
    if values['rod_worth'] <= 0.0:
        problems.append('rod_worth must be positive')
    if values['temp_coefficient'] > 0.0:
        problems.append('temp_coefficient must be non-positive')
    if values['void_coefficient'] < 0.0:
        problems.append('void_coefficient must be non-negative')
    if values['xenon_worth'] < 0.0 or values['xenon_yield'] < 0.0:
        problems.append('xenon parameters must be non-negative')
    if problems:
        raise ValueError('assembly on %s is out of bounds: %s' % (base_key, '; '.join(problems)))


def assemble(name, module_keys, base_key='base') -> Blueprint:
    if base_key not in BLUEPRINTS:
        raise KeyError('unknown blueprint: ' + str(base_key))
    base = BLUEPRINTS[base_key]
    modules = resolve_modules(module_keys)
    for module in modules:
        if module.tier > base.tier + MAX_TIER_OFFSET:
            raise ValueError('module %s is too advanced for blueprint %s' % (module.key, base_key))
    factors = {field: 1.0 for field in MODIFIER_FIELDS}
    for module in modules:
        for field in MODIFIER_FIELDS:
            factors[field] *= getattr(module, field)
    values = {field: getattr(base, field) * factors[field] for field in MODIFIER_FIELDS}
    _check_bounds(values, base_key)
    durability = sum(module.durability for module in modules) / len(modules)
    return replace(
        base,
        name=name,
        build_cost=base.build_cost + assemble_cost(module_keys),
        build_time=base.build_time * (1.0 + BUILD_TIME_DURABILITY * (1.0 - durability)),
        components=base.components + tuple(module.name for module in modules),
        **values,
    )


def efficiency_score(blueprint):
    return blueprint.rated_power * blueprint.efficiency / blueprint.build_cost


def ready_of_same_price(blueprint):
    return min(BLUEPRINTS.values(), key=lambda item: abs(item.build_cost - blueprint.build_cost))


def compare_with_ready(blueprint):
    ready = ready_of_same_price(blueprint)
    gain = efficiency_score(blueprint) / efficiency_score(ready) - 1.0
    return ready, gain


def best_set(base_key):
    limit = BLUEPRINTS[base_key].tier + MAX_TIER_OFFSET
    keys = []
    for slot in SLOTS:
        allowed = [MODULES[key] for key in SLOT_MODULES[slot] if MODULES[key].tier <= limit]
        keys.append(max(allowed, key=lambda module: (module.tier, module.price)).key)
    return tuple(keys)


__all__ = [
    'MAX_TIER_OFFSET',
    'MODIFIER_FIELDS',
    'MODULES',
    'Module',
    'SLOTS',
    'SLOT_MODULES',
    'TIER_PRICE',
    'assemble',
    'assemble_cost',
    'best_set',
    'compare_with_ready',
    'efficiency_score',
    'ready_of_same_price',
    'resolve_modules',
]
