import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, Tuple


BETA = 0.0065
LAMBDA_DELAYED = 0.08
LAMBDA_IODINE = 2.9e-5
LAMBDA_XENON = 2.1e-5
XENON_BURNUP = 1.0e-4
XENON_REFERENCE = 1.4
T_INLET = 280.0
T_REFERENCE = 280.0
P_NOMINAL = 12.0
T_SAT_COEFF = 177.8
PROMPT_MARGIN = 0.95
SOURCE_NEUTRONS = 1.0e-10
MAX_POWER_FRACTION = 4.0
TEMP_CEILING = 5000.0
PRESSURE_CEILING = 400.0
VOID_SPAN = 60.0
VOID_PRESSURE_GAIN = 0.8
PRESSURE_TAU = 20.0
DECAY_FRACTION = 0.065
DECAY_TAU = 1200.0
MAX_SUBSTEP = 2.0
MAX_SUBSTEPS = 20000
INITIAL_POWER = 1.0e-3
MAX_EXPONENT = 5.0
POWER_FLOOR = 1.0e-12

WEAR_SLOTS = ('hull', 'fuel', 'rods', 'pump', 'turbine', 'shield')

WEAR_NAMES = {
    'hull': 'Корпус',
    'fuel': 'Топливо',
    'rods': 'Стержни',
    'pump': 'Насос',
    'turbine': 'Турбина',
    'shield': 'Защита',
}

# Нижняя граница характеристики полностью убитого модуля: значение 0.0
# означает, что сломанный модуль вообще перестаёт работать, 1.0 — что
# характеристики от износа не падают.
WEAR_FLOORS = {
    'hull': 0.82,
    'fuel': 0.70,
    'rods': 0.62,
    'pump': 0.45,
    'turbine': 0.60,
    'shield': 0.88,
}

# Сколько секунд нужно, чтобы полностью износить модуль при 100 % нагрузки
# и difficulty = 1. Скорость износа умножается на текущую нагрузку и на
# difficulty чертежа, поэтому базовый блок расходует ресурс медленнее.
WEAR_FULL_TIME = 900.0
WEAR_BASE_RATE = 1.0 / WEAR_FULL_TIME
# Аркада: износ в 2 раза медленнее Нормала, Хардкор: в 1.5 раза быстрее.
WEAR_REALISM_SCALE = {'arcade': 0.5, 'normal': 1.0, 'hardcore': 1.5}

# Пороги предупреждений: остаток прочности ниже 30 % и ниже 10 %.
WEAR_WARN_LEVEL = 0.30
WEAR_CRITICAL_LEVEL = 0.10

# Вклад режима работы в износ каждого слота: load — выработка, thermal —
# температура, pressure — давление. Сумма весов ~1.0 при полной нагрузке.
WEAR_SENSITIVITY = {
    'hull': {'load': 0.20, 'thermal': 0.55, 'pressure': 0.45},
    'fuel': {'load': 1.00, 'thermal': 0.25, 'pressure': 0.05},
    'rods': {'load': 0.70, 'thermal': 0.10, 'pressure': 0.20},
    'pump': {'load': 0.60, 'thermal': 0.40, 'pressure': 0.25},
    'turbine': {'load': 0.90, 'thermal': 0.10, 'pressure': 0.15},
    'shield': {'load': 0.10, 'thermal': 0.50, 'pressure': 0.50},
}

# Поломка этих слотов сама по себе останавливает реактор (АЗ-5).
WEAR_SCRAM_SLOTS = ('hull', 'pump', 'rods')


class RealismLevel(Enum):
    ARCADE = 'arcade'
    NORMAL = 'normal'
    HARDCORE = 'hardcore'


class ReactorState(Enum):
    COLD = 'cold'
    SHUTDOWN = 'shutdown'
    CRITICAL = 'critical'
    SUPERCRITICAL = 'supercritical'
    SCRAM = 'scram'
    MELTDOWN = 'meltdown'


class FailureMode(Enum):
    NONE = 'none'
    OVERHEAT = 'overheat'
    OVERPRESSURE = 'overpressure'
    OVERPOWER = 'overpower'
    PROMPT_CRITICAL = 'prompt_critical'


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def saturation_temperature(pressure):
    return T_SAT_COEFF * max(pressure, 1.0e-3) ** 0.25


def saturation_pressure(temperature):
    return (max(temperature, 1.0) / T_SAT_COEFF) ** 4


@dataclass(frozen=True)
class RealismProfile:
    level: RealismLevel
    response_scale: float
    rod_scale: float
    feedback_scale: float
    xenon_scale: float
    void_scale: float
    pressure_scale: float
    thermal_inertia: float
    limit_scale: float
    decay_heat_scale: float
    grace_period: float
    kinetics_gain: float


REALISM_PROFILES = {
    RealismLevel.ARCADE: RealismProfile(RealismLevel.ARCADE, 0.35, 0.9, 1.6, 0.4, 0.0, 0.6, 2.2, 1.4, 0.6, 20.0, 22.0),
    RealismLevel.NORMAL: RealismProfile(RealismLevel.NORMAL, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 15.0),
    RealismLevel.HARDCORE: RealismProfile(RealismLevel.HARDCORE, 1.15, 1.1, 1.25, 1.3, 1.5, 1.2, 0.85, 0.95, 1.15, 0.0, 12.0),
}


@dataclass(frozen=True)
class Blueprint:
    name: str
    tier: int
    difficulty: float
    build_cost: float
    build_time: float
    components: Tuple[str, ...]
    rated_power: float
    max_power: float
    efficiency: float
    temp_limit: float
    pressure_limit: float
    rod_worth: float
    temp_coefficient: float
    void_coefficient: float
    xenon_worth: float
    xenon_yield: float

    def __post_init__(self):
        if self.tier < 1:
            raise ValueError('tier must be at least 1')
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError('difficulty must be within [0, 1]')
        if self.rated_power <= 0.0:
            raise ValueError('rated_power must be positive')
        if self.max_power < self.rated_power:
            raise ValueError('max_power must not be below rated_power')
        if not 0.0 < self.efficiency < 1.0:
            raise ValueError('efficiency must be between 0 and 1')
        if self.build_cost <= 0.0 or self.build_time <= 0.0:
            raise ValueError('build_cost and build_time must be positive')
        if self.temp_limit <= T_REFERENCE:
            raise ValueError('temp_limit must exceed reference temperature')
        if self.pressure_limit <= P_NOMINAL:
            raise ValueError('pressure_limit must exceed nominal pressure')
        if self.rod_worth <= 0.0:
            raise ValueError('rod_worth must be positive')
        if self.temp_coefficient > 0.0:
            raise ValueError('temp_coefficient must be non-positive')
        if self.void_coefficient < 0.0:
            raise ValueError('void_coefficient must be non-negative')
        if self.xenon_worth < 0.0 or self.xenon_yield < 0.0:
            raise ValueError('xenon parameters must be non-negative')
        if not self.components:
            raise ValueError('components must not be empty')

    @property
    def thermal_power(self):
        return self.rated_power / self.efficiency

    @property
    def rod_excess(self):
        return self.rod_worth * 0.75

    @property
    def rod_excess_pcm(self):
        return self.rod_excess * 1.0e5

    @property
    def shock_potential(self):
        return (self.rod_excess + self.void_coefficient) / BETA

    @property
    def meltdown_potential(self):
        return clamp((self.void_coefficient + self.xenon_worth) / BETA, 0.0, 1.0)


BLUEPRINTS: Dict[str, Blueprint] = {
    'base': Blueprint('Базовый', 1, 0.15, 5000.0, 60.0, ('корпус «Купол-1»', 'графитовая кладка «Хвоя»', 'борные стержни БШ-4 «Гвоздика»', 'насос первого контура «Ручей»'), 10.0, 40.0, 0.30, 900.0, 14.0, 0.0042, -1.2e-5, 0.0, 0.008, 1.0),
    'medium': Blueprint('Средний', 2, 0.35, 250000.0, 900.0, ('корпус высокого давления', 'парогенератор', 'стержни с приводом', 'главный циркуляционный насос', 'система аварийного охлаждения'), 250.0, 1000.0, 0.33, 950.0, 15.0, 0.0046, -1.3e-5, 0.0015, 0.009, 1.05),
    'high': Blueprint('Высокий', 3, 0.55, 20000000.0, 7200.0, ('усиленный корпус', 'многоконтурный парогенератор', 'борная система', 'турбина высокого давления', 'резервные насосы'), 5000.0, 20000.0, 0.36, 1000.0, 16.0, 0.0050, -1.4e-5, 0.003, 0.010, 1.1),
    'extreme': Blueprint('Экстрим', 4, 0.8, 5000000000.0, 86400.0, ('композитный корпус', 'плутониевое топливо', 'жидкометаллический теплоноситель', 'каскад турбин', 'система подавления пара', 'дублирующая защита'), 120000.0, 480000.0, 0.39, 1050.0, 17.5, 0.0055, -1.5e-5, 0.0045, 0.011, 1.2),
    'impossible': Blueprint('Невозможный', 5, 1.0, 2000000000000.0, 604800.0, ('экзотический сплав', 'торальная геометрия', 'сверхпроводящие магниты', 'прямой цикл', 'наноуправляемые стержни', 'квантовая защита', 'резонансный теплоноситель'), 2500000.0, 10000000.0, 0.42, 1100.0, 20.0, 0.0058, -1.6e-5, 0.006, 0.012, 1.3),
}


CUSTOM_POWER_RATIO = 0.82
CUSTOM_EFFICIENCY_RATIO = 0.93
CUSTOM_POWER_CEILING = 0.85


def make_custom(name='Свой', **overrides):
    top = BLUEPRINTS['impossible']
    blueprint = replace(
        top,
        name=name,
        tier=5,
        difficulty=1.0,
        build_cost=top.build_cost * 0.8,
        build_time=top.build_time * 1.15,
        components=top.components + ('кастомный контроллер', 'авторский теплообменник'),
        rated_power=top.rated_power * CUSTOM_POWER_RATIO,
        max_power=top.max_power * CUSTOM_POWER_RATIO,
        efficiency=top.efficiency * CUSTOM_EFFICIENCY_RATIO,
        rod_worth=top.rod_worth * 0.95,
        xenon_worth=top.xenon_worth * 1.05,
    )
    if overrides:
        blueprint = replace(blueprint, **overrides)
    if blueprint.rated_power > top.rated_power * CUSTOM_POWER_CEILING:
        raise ValueError('custom blueprint exceeds allowed power')
    if blueprint.max_power > top.max_power * CUSTOM_POWER_CEILING:
        raise ValueError('custom blueprint exceeds allowed peak power')
    if blueprint.efficiency >= top.efficiency:
        raise ValueError('custom blueprint exceeds allowed efficiency')
    if blueprint.rod_worth >= top.rod_worth:
        raise ValueError('custom blueprint exceeds allowed rod worth')
    return blueprint


BLUEPRINTS['custom'] = make_custom()


class Reactor:
    def __init__(self, blueprint, realism=RealismLevel.NORMAL, time_scale=1.0, initial_rod_position=1.0):
        if not isinstance(blueprint, Blueprint):
            raise TypeError('blueprint must be a Blueprint instance')
        if isinstance(realism, RealismLevel):
            profile = REALISM_PROFILES[realism]
        elif isinstance(realism, RealismProfile):
            profile = realism
        else:
            raise TypeError('realism must be RealismLevel or RealismProfile')
        if time_scale <= 0.0:
            raise ValueError('time_scale must be positive')
        self.blueprint = blueprint
        self.realism = profile
        self.time_scale = float(time_scale)
        self.q_rated = blueprint.thermal_power
        self.fuel_capacity = self.q_rated * 1.5 * profile.thermal_inertia
        self.coolant_capacity = self.q_rated * 8.0 * profile.thermal_inertia
        self.heat_transfer = self.q_rated / 120.0
        self.coolant_removal = self.q_rated / 18.0
        self.rod_position = clamp(initial_rod_position)
        self.coolant_flow = 1.0
        self.power = INITIAL_POWER
        self.iodine = 0.0
        self.xenon = 0.0
        self.decay_heat = 0.0
        self.fuel_temp = T_INLET
        self.coolant_temp = T_INLET
        self.pressure = P_NOMINAL
        self.void_fraction = 0.0
        self.time = 0.0
        self.overlimit_time = 0.0
        self.destroyed = False
        self.scrammed = False
        self.failure = FailureMode.NONE
        self.meltdown_time = None
        self.state = ReactorState.COLD
        self.wear = {slot: 1.0 for slot in WEAR_SLOTS}
        self.broken = set()
        self.wear_enabled = True
        self.wear_log = []
        self.wear_break_count = 0
        self.wear_messages = []
        self.wear_alerts = {}
        self.logger = None

    # --------------------------------------------------------------- износ

    def wear_factor(self, slot):
        """Множитель характеристики слота: 1.0 — новый, floor — убитый."""
        floor = WEAR_FLOORS[slot]
        return floor + (1.0 - floor) * clamp(self.wear.get(slot, 1.0))

    @property
    def limit_wear_scale(self):
        hull = self.wear_factor('hull')
        shield = self.wear_factor('shield')
        return math.sqrt(hull * shield)

    @property
    def power_wear_scale(self):
        return self.wear_factor('fuel') * self.wear_factor('turbine')

    @property
    def rod_wear_scale(self):
        return self.wear_factor('rods')

    @property
    def coolant_wear_scale(self):
        return self.wear_factor('pump')

    @property
    def wear_overall(self):
        if not self.wear:
            return 1.0
        return sum(self.wear.get(slot, 1.0) for slot in WEAR_SLOTS) / len(WEAR_SLOTS)

    @property
    def wear_broken_slots(self):
        return tuple(slot for slot in WEAR_SLOTS if slot in self.broken)

    def _wear_emit(self, message):
        self.wear_log.append(message)
        if len(self.wear_log) > 100:
            del self.wear_log[:50]
        self.wear_messages.append(message)
        if self.logger is not None:
            self.logger(message)

    def drain_wear_messages(self):
        messages = self.wear_messages
        self.wear_messages = []
        return messages

    def wear_rate(self, slot, load, thermal, pressure):
        sens = WEAR_SENSITIVITY[slot]
        if slot in self.broken:
            return 0.0
        intensity = (
            sens['load'] * load
            + sens['thermal'] * max(0.0, thermal - 0.55)
            + sens['pressure'] * max(0.0, pressure - 0.55)
        )
        intensity = max(intensity, sens['load'] * 0.08)
        difficulty = 0.6 + 0.8 * self.blueprint.difficulty
        realism = WEAR_REALISM_SCALE.get(self.realism.level.value, 1.0)
        return WEAR_BASE_RATE * difficulty * realism * intensity

    def repair_slot(self, slot, amount=1.0):
        if slot not in WEAR_SLOTS:
            raise KeyError('unknown wear slot: ' + str(slot))
        before = self.wear.get(slot, 1.0)
        self.wear[slot] = clamp(before + amount)
        if self.wear[slot] > 0.02:
            self.broken.discard(slot)
        return self.wear[slot] - before

    def _break_module(self, slot):
        if slot in self.broken:
            return
        self.broken.add(slot)
        self.wear[slot] = 0.0
        self.wear_break_count += 1
        self._wear_emit(
            'ПОЛОМКА: %s (%s) выработал ресурс'
            % (WEAR_NAMES.get(slot, slot), slot)
        )
        if slot in WEAR_SCRAM_SLOTS and not self.destroyed:
            if not self.scrammed:
                self.scrammed = True
                self.rod_position = 1.0
                self._update_state()
            self._wear_emit('АЗ-5: автоматическая остановка из-за поломки')

    def _check_wear_alerts(self, slot):
        """Разовые предупреждения при пересечении порогов износа."""
        state = self.wear_alerts.setdefault(slot, {'warn': False, 'critical': False})
        value = self.wear.get(slot, 1.0)
        name = WEAR_NAMES.get(slot, slot)
        if not state['warn'] and value < WEAR_WARN_LEVEL:
            state['warn'] = True
            worn_percent = int(round((1.0 - value) * 100.0))
            self._wear_emit('ВНИМАНИЕ: %s изношен на %d%%' % (name, worn_percent))
        if not state['critical'] and value < WEAR_CRITICAL_LEVEL:
            state['critical'] = True
            self._wear_emit('КРИТИЧЕСКИЙ ИЗНОС: %s скоро сломается!' % name)

    def _integrate_wear(self, dt):
        if not self.wear_enabled or self.destroyed:
            return
        load = clamp(self.power * self.blueprint.rated_power / max(self.blueprint.rated_power, 1.0e-9), 0.0, 1.4)
        thermal = self.fuel_temp / max(self.temp_limit_effective, 1.0e-9)
        pressure = self.pressure / max(self.pressure_limit_effective, 1.0e-9)
        for slot in WEAR_SLOTS:
            if slot in self.broken:
                continue
            delta = self.wear_rate(slot, load, thermal, pressure) * dt
            if delta <= 0.0:
                continue
            self.wear[slot] = clamp(self.wear.get(slot, 1.0) - delta)
            self._check_wear_alerts(slot)
            if self.wear[slot] <= 0.0:
                self._break_module(slot)

    @property
    def thermal_power_mw(self):
        return (self.power + self.decay_heat) * self.q_rated

    @property
    def electrical_power_mw(self):
        if self.destroyed:
            return 0.0
        return self.power * self.blueprint.rated_power * self.power_wear_scale

    @property
    def power_fraction_of_max(self):
        return self.power * self.blueprint.rated_power / self.blueprint.max_power

    @property
    def rod_reactivity(self):
        return (
            self.blueprint.rod_worth
            * (0.75 - self.rod_position)
            * self.realism.rod_scale
            * self.rod_wear_scale
        )

    @property
    def effective_coolant_flow(self):
        return self.coolant_flow * self.coolant_wear_scale

    @property
    def temperature_reactivity(self):
        return self.blueprint.temp_coefficient * (self.fuel_temp - T_REFERENCE) * self.realism.feedback_scale

    @property
    def xenon_poison(self):
        fraction = 1.0 - math.exp(-self.xenon / XENON_REFERENCE)
        return self.blueprint.xenon_worth * fraction * self.realism.xenon_scale

    @property
    def xenon_reactivity(self):
        return -self.xenon_poison

    @property
    def void_reactivity(self):
        return self.blueprint.void_coefficient * self.void_fraction * self.realism.void_scale

    @property
    def reactivity(self):
        return self.rod_reactivity + self.temperature_reactivity + self.xenon_reactivity + self.void_reactivity

    @property
    def reactivity_pcm(self):
        return self.reactivity * 1.0e5

    @property
    def reactivity_dollars(self):
        return self.reactivity / BETA

    @property
    def prompt_critical(self):
        return self.reactivity >= BETA

    @property
    def period(self):
        if self.destroyed:
            return 0.0
        if self.reactivity >= BETA:
            return math.inf
        denominator = LAMBDA_DELAYED * self.reactivity * self.realism.response_scale
        if abs(denominator) < 1.0e-12:
            return math.inf
        return (BETA - self.reactivity) / denominator

    @property
    def temp_limit_effective(self):
        return self.blueprint.temp_limit * self.realism.limit_scale * self.limit_wear_scale

    @property
    def pressure_limit_effective(self):
        return self.blueprint.pressure_limit * self.realism.limit_scale * self.limit_wear_scale

    @property
    def power_limit_effective(self):
        return self.blueprint.max_power * self.realism.limit_scale

    @property
    def saturation(self):
        return saturation_temperature(self.pressure)

    @property
    def subcooling(self):
        return self.saturation - self.coolant_temp

    @property
    def stress(self):
        if self.destroyed:
            return 1.0
        return max(
            self.fuel_temp / self.temp_limit_effective,
            self.pressure / self.pressure_limit_effective,
            self.power * self.blueprint.rated_power / self.power_limit_effective,
        )

    @property
    def time_to_limit(self):
        if self.destroyed:
            return 0.0
        heat_in = (self.power + self.decay_heat * self.realism.decay_heat_scale) * self.q_rated
        heat_out = self.heat_transfer * (self.fuel_temp - self.coolant_temp)
        net = heat_in - heat_out
        if net <= 0.0:
            return math.inf
        headroom = max(self.temp_limit_effective - self.fuel_temp, 0.0)
        return headroom * self.fuel_capacity / net

    @property
    def reactivity_components(self):
        return {
            'rods': self.rod_reactivity,
            'temperature': self.temperature_reactivity,
            'xenon': self.xenon_reactivity,
            'void': self.void_reactivity,
            'total': self.reactivity,
        }

    def set_rod_position(self, position):
        if self.destroyed:
            return False
        if self.scrammed:
            return False
        self.rod_position = clamp(position)
        self._update_state()
        return True

    def move_rods(self, delta):
        return self.set_rod_position(self.rod_position + delta)

    def set_coolant_flow(self, flow):
        if self.destroyed:
            return False
        self.coolant_flow = clamp(flow)
        return True

    def scram(self):
        if self.destroyed:
            return False
        self.scrammed = True
        self.rod_position = 1.0
        self._update_state()
        return True

    def reset_scram(self):
        if self.destroyed:
            return False
        self.scrammed = False
        self.rod_position = 1.0
        self._update_state()
        return True

    def step(self, dt):
        if dt <= 0.0:
            raise ValueError('dt must be positive')
        if self.destroyed:
            return self.snapshot()
        dt_effective = dt * self.time_scale
        steps = min(MAX_SUBSTEPS, max(1, int(math.ceil(dt_effective / MAX_SUBSTEP))))
        h = dt_effective / steps
        for _ in range(steps):
            self._integrate(h)
            if self.destroyed:
                break
        return self.snapshot()

    def _integrate(self, dt):
        self.time += dt
        rho = self.reactivity
        if rho >= BETA * PROMPT_MARGIN:
            self._destroy(FailureMode.PROMPT_CRITICAL)
            return
        base = max(self.power, POWER_FLOOR)
        growth = (
            LAMBDA_DELAYED
            * rho
            / (BETA - rho)
            * self.realism.response_scale
            * self.realism.kinetics_gain
        )
        exponent = clamp(growth * dt, -30.0, 30.0)
        self.power = clamp(
            base * math.exp(exponent) + SOURCE_NEUTRONS * dt,
            POWER_FLOOR,
            MAX_POWER_FRACTION,
        )
        self._integrate_xenon(dt)
        self._integrate_thermal(dt)
        self._integrate_pressure(dt)
        self._check_damage(dt)
        self._integrate_wear(dt)
        self._update_state()

    def _integrate_xenon(self, dt):
        source = self.power * self.blueprint.xenon_yield
        d_iodine = LAMBDA_IODINE * (source - self.iodine)
        d_xenon = LAMBDA_IODINE * (0.05 * source + self.iodine) - (LAMBDA_XENON + XENON_BURNUP * self.power) * self.xenon
        self.iodine = max(0.0, self.iodine + d_iodine * dt)
        self.xenon = max(0.0, self.xenon + d_xenon * dt)

    def _integrate_thermal(self, dt):
        target_decay = DECAY_FRACTION * self.power
        self.decay_heat += (target_decay - self.decay_heat) * dt / DECAY_TAU
        self.decay_heat = max(0.0, self.decay_heat)
        heat_in = (self.power + self.decay_heat * self.realism.decay_heat_scale) * self.q_rated
        transfer = self.heat_transfer * (self.fuel_temp - self.coolant_temp)
        self.fuel_temp += (heat_in - transfer) * dt / self.fuel_capacity
        removal = self.coolant_removal * self.effective_coolant_flow * max(0.0, self.coolant_temp - T_INLET)
        self.coolant_temp += (transfer - removal) * dt / self.coolant_capacity
        self.fuel_temp = clamp(self.fuel_temp, T_INLET, TEMP_CEILING)
        self.coolant_temp = clamp(self.coolant_temp, T_INLET, TEMP_CEILING)

    def _integrate_pressure(self, dt):
        superheat = max(0.0, self.coolant_temp - self.saturation)
        self.void_fraction = clamp(superheat / VOID_SPAN)
        target = P_NOMINAL * (1.0 + VOID_PRESSURE_GAIN * self.void_fraction * self.realism.void_scale)
        rate = (target - self.pressure) / PRESSURE_TAU * self.realism.pressure_scale
        self.pressure = clamp(self.pressure + rate * dt, 0.1, PRESSURE_CEILING)

    def _check_damage(self, dt):
        mode = FailureMode.NONE
        if self.fuel_temp >= self.temp_limit_effective:
            mode = FailureMode.OVERHEAT
        if self.pressure >= self.pressure_limit_effective:
            mode = FailureMode.OVERPRESSURE
        if self.power * self.blueprint.rated_power >= self.power_limit_effective:
            mode = FailureMode.OVERPOWER
        if mode is FailureMode.NONE:
            self.overlimit_time = max(0.0, self.overlimit_time - dt * 0.5)
            return
        self.overlimit_time += dt
        if self.overlimit_time > self.realism.grace_period:
            self._destroy(mode)

    def _destroy(self, mode):
        if self.destroyed:
            return
        self.destroyed = True
        self.failure = mode
        self.state = ReactorState.MELTDOWN
        self.meltdown_time = self.time
        self.power = 0.0
        self.overlimit_time = max(self.overlimit_time, self.realism.grace_period)

    def _update_state(self):
        if self.destroyed:
            self.state = ReactorState.MELTDOWN
        elif self.scrammed:
            self.state = ReactorState.SCRAM
        elif self.power < 1.0e-6 and self.fuel_temp <= T_INLET + 5.0:
            self.state = ReactorState.COLD
        elif self.power < 1.0e-4:
            self.state = ReactorState.SHUTDOWN
        elif self.reactivity > 1.0e-6:
            self.state = ReactorState.SUPERCRITICAL
        else:
            self.state = ReactorState.CRITICAL

    def snapshot(self):
        return {
            'time': round(self.time, 3),
            'state': self.state.value,
            'failure': self.failure.value,
            'destroyed': self.destroyed,
            'power_frac': round(self.power, 8),
            'thermal_power_mw': round(self.thermal_power_mw, 3),
            'electrical_power_mw': round(self.electrical_power_mw, 3),
            'rated_power_mw': self.blueprint.rated_power,
            'reactivity': round(self.reactivity, 8),
            'reactivity_pcm': round(self.reactivity_pcm, 2),
            'reactivity_dollars': round(self.reactivity_dollars, 4),
            'period_s': round(self.period, 2) if self.period != math.inf else None,
            'rod_position': round(self.rod_position, 4),
            'coolant_flow': round(self.coolant_flow, 4),
            'fuel_temp': round(self.fuel_temp, 2),
            'coolant_temp': round(self.coolant_temp, 2),
            'saturation_temp': round(self.saturation, 2),
            'subcooling': round(self.subcooling, 2),
            'pressure': round(self.pressure, 3),
            'void_fraction': round(self.void_fraction, 4),
            'iodine': round(self.iodine, 6),
            'xenon': round(self.xenon, 6),
            'xenon_poison': round(self.xenon_poison, 8),
            'decay_heat': round(self.decay_heat, 6),
            'stress': round(self.stress, 4),
            'overlimit_time': round(self.overlimit_time, 2),
            'prompt_critical': self.prompt_critical,
            'wear': {slot: round(value, 4) for slot, value in self.wear.items()},
            'wear_overall': round(self.wear_overall, 4),
            'broken': tuple(sorted(self.broken)),
        }

    def __repr__(self):
        return 'Reactor(name=%r, state=%s, power=%.3f, temp=%.1f, pressure=%.2f)' % (
            self.blueprint.name,
            self.state.value,
            self.electrical_power_mw,
            self.fuel_temp,
            self.pressure,
        )


def create_reactor(blueprint_key='base', realism=RealismLevel.NORMAL, time_scale=1.0, initial_rod_position=1.0):
    if blueprint_key not in BLUEPRINTS:
        raise KeyError('unknown blueprint: ' + str(blueprint_key))
    return Reactor(BLUEPRINTS[blueprint_key], realism, time_scale, initial_rod_position)


def list_blueprints():
    return dict(BLUEPRINTS)


def custom_blueprint(**overrides):
    return make_custom(**overrides)


__all__ = [
    'BETA',
    'Blueprint',
    'BLUEPRINTS',
    'FailureMode',
    'REALISM_PROFILES',
    'Reactor',
    'ReactorState',
    'RealismLevel',
    'RealismProfile',
    'clamp',
    'create_reactor',
    'custom_blueprint',
    'list_blueprints',
    'make_custom',
    'saturation_pressure',
    'saturation_temperature',
]
