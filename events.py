import random

from reactor_core import clamp


class ActiveEvent:
    def __init__(self, key, title, duration, undo):
        self.key = key
        self.title = title
        self.remaining = duration
        self.duration = duration
        self.undo = undo


class RandomEventManager:
    def __init__(self, reactor, logger=None, seed=None, min_delay=35.0, max_delay=80.0):
        self.reactor = reactor
        self.logger = logger
        self.rng = random.Random(seed)
        self.min_delay = float(min_delay)
        self.max_delay = float(max_delay)
        self.elapsed = 0.0
        self.next_event = self._roll_delay()
        self.active = []
        self.history = []
        self.enabled = True
        self.scenario = False
        self.scenario_time = 0.0
        self.pumps_off = 0
        self.next_pump_shutdown = 0.0
        self.next_reactivity_drop = 0.0

    def _roll_delay(self):
        return self.rng.uniform(self.min_delay, self.max_delay)

    def _emit(self, message):
        self.history.append(message)
        if len(self.history) > 200:
            del self.history[:100]
        if self.logger is not None:
            self.logger(message)

    def start_chernobyl(self):
        if self.scenario:
            return False
        self.scenario = True
        self.scenario_time = 0.0
        self.next_pump_shutdown = 20.0
        self.next_reactivity_drop = 30.0
        self._emit("СЦЕНАРИЙ ЧЕРНОБЫЛЯ: начата проверка выбега турбины")
        return True

    def stop_chernobyl(self):
        self.scenario = False
        self._emit("СЦЕНАРИЙ ЧЕРНОБЫЛЯ: остановлен")

    def update(self, dt):
        if dt <= 0.0:
            return
        reactor = self.reactor
        if reactor.destroyed:
            return
        self._update_active(dt)
        if self.scenario:
            self._update_scenario(dt)
        if not self.enabled:
            return
        self.elapsed += dt
        if self.elapsed >= self.next_event:
            self.elapsed = 0.0
            self.next_event = self._roll_delay()
            self.trigger_random()

    def _update_active(self, dt):
        for event in list(self.active):
            event.remaining -= dt
            if event.remaining > 0.0:
                continue
            self.active.remove(event)
            if event.undo is not None:
                event.undo(self.reactor)
            self._emit("Событие «%s» завершилось" % event.title)

    def _update_scenario(self, dt):
        self.scenario_time += dt
        if self.scenario_time >= self.next_pump_shutdown:
            self.next_pump_shutdown = self.scenario_time + self.rng.uniform(18.0, 26.0)
            self._shutdown_pump()
        if self.scenario_time >= self.next_reactivity_drop:
            self.next_reactivity_drop = self.scenario_time + self.rng.uniform(22.0, 32.0)
            self._drop_reactivity()

    def _shutdown_pump(self):
        reactor = self.reactor
        if reactor.destroyed:
            return
        step = self.rng.uniform(0.14, 0.2)
        reactor.set_coolant_flow(clamp(reactor.coolant_flow - step))
        self.pumps_off += 1
        self._emit("СЦЕНАРИЙ ЧЕРНОБЫЛЯ: отключён насос ГЦН-%d (подача %.0f%%)" % (self.pumps_off, reactor.coolant_flow * 100.0))

    def _drop_reactivity(self):
        reactor = self.reactor
        if reactor.destroyed:
            return
        before = reactor.reactivity
        inserted = False
        if not reactor.scrammed:
            inserted = reactor.move_rods(0.035)
        self._emit("СЦЕНАРИЙ ЧЕРНОБЫЛЯ: реактивность падает (%+.3f -> %+.3f)" % (before, reactor.reactivity))

    def trigger_random(self):
        reactor = self.reactor
        if reactor.destroyed or reactor.scrammed:
            return None
        key = self.rng.choices(("crack", "sensor", "surge"), weights=(4, 3, 3))[0]
        if key == "crack":
            return self.trigger_crack()
        if key == "sensor":
            return self.trigger_sensor_failure()
        return self.trigger_voltage_surge()

    def trigger_crack(self):
        reactor = self.reactor
        if reactor.destroyed:
            return None
        reactor.set_coolant_flow(clamp(reactor.coolant_flow * 0.75))
        self._emit("АВАРИЯ: трещина в контуре охлаждения, подача %.0f%%" % (reactor.coolant_flow * 100.0))
        return "crack"

    def trigger_sensor_failure(self):
        reactor = self.reactor
        if reactor.destroyed:
            return None
        duration = self.rng.uniform(20.0, 35.0)
        factor = 0.88
        reactor.set_coolant_flow(clamp(reactor.coolant_flow * factor))
        reactor.fuel_temp += 12.0

        def undo(target, factor=factor):
            if not target.destroyed:
                target.set_coolant_flow(clamp(target.coolant_flow / factor))

        self.active.append(ActiveEvent("sensor", "Отказ датчика", duration, undo))
        self._emit("АВАРИЯ: отказ датчика температуры, регулятор сбросил подачу охлаждения")
        return "sensor"

    def trigger_voltage_surge(self):
        reactor = self.reactor
        if reactor.destroyed:
            return None
        reactor.power = min(reactor.power * self.rng.uniform(1.05, 1.09), 1.0)
        self._emit("АВАРИЯ: скачок напряжения в сети, мощность реактора %.0f%%" % (reactor.power * 100.0))
        return "surge"
