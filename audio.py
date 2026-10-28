import math
import random
from array import array
from collections import deque

from PySide6.QtCore import QIODevice, QObject
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices


SAMPLE_RATE = 44100
TABLE_SIZE = 2048
TABLE = [math.sin(2.0 * math.pi * i / TABLE_SIZE) for i in range(TABLE_SIZE)]
CLICK_FRAMES = 1400
SMOOTHING = 0.00008


def _clamp(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _wave(phase):
    return TABLE[int(phase * TABLE_SIZE) & (TABLE_SIZE - 1)]


class _SynthDevice(QIODevice):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine

    def isSequential(self):
        return True

    def readData(self, maxlen):
        return self._engine.render(max(0, int(maxlen)))

    def writeData(self, _data):
        return -1

    def bytesAvailable(self):
        return 8192 + super().bytesAvailable()


class AudioEngine(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = False
        self.muted = False
        self._master = 0.55
        self._phases = [0.0, 0.0, 0.0, 0.0]
        self._hum = 0.0
        self._hum_target = 0.0
        self._freq = 40.0
        self._freq_target = 40.0
        self._hiss = 0.0
        self._hiss_target = 0.0
        self._siren = 0.0
        self._siren_target = 0.0
        self._siren_time = 0.0
        self._noise_prev = 0.0
        self._click_queue = deque()
        self._click_left = 0
        self._click_amp = 0.0
        self._sink = None
        self._device = None
        self._format = QAudioFormat()
        self._format.setSampleRate(SAMPLE_RATE)
        self._format.setChannelCount(1)
        self._format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._start_output()

    def _start_output(self):
        try:
            output = QMediaDevices.defaultAudioOutput()
            if output is None or output.isNull():
                return
            sink = QAudioSink(output, self._format, self)
            sink.setBufferSize(32768)
            source = _SynthDevice(self)
            source.open(QIODevice.OpenModeFlag.ReadOnly)
            sink.start(source)
            if sink.state() == QAudio.State.StoppedState:
                sink.stop()
                source.close()
                return
            self._sink = sink
            self._device = source
            self.enabled = True
        except Exception:
            self._sink = None
            self._device = None
            self.enabled = False

    def set_muted(self, muted):
        self.muted = bool(muted)
        if self._sink is not None:
            self._sink.setVolume(0.0 if self.muted else self._master)

    def play_click(self, strength=0.35):
        if not self.enabled:
            return
        if len(self._click_queue) < 6:
            self._click_queue.append(float(strength))

    def update(self, fuel_ratio, pressure_ratio, power_ratio, xenon_ratio, alarm, destroyed):
        power = _clamp(power_ratio)
        pressure = _clamp(pressure_ratio)
        fuel = _clamp(fuel_ratio)
        if destroyed:
            self._hum_target = 0.0
            self._hiss_target = 0.30
            self._siren_target = 0.0
            return
        self._hum_target = 0.10 + 0.22 * power
        self._freq_target = 38.0 + 64.0 * power + 8.0 * pressure
        steam = 0.0
        if pressure > 0.70:
            steam = (pressure - 0.70) / 0.30
        if fuel > 0.88:
            steam = max(steam, (fuel - 0.88) / 0.12 * 0.8)
        self._hiss_target = 0.34 * steam
        critical = fuel >= 0.999 or pressure >= 0.999 or power >= 0.999
        self._siren_target = 0.30 if critical else 0.0

    def stop(self):
        sink = self._sink
        device = self._device
        self._sink = None
        self._device = None
        self.enabled = False
        try:
            if sink is not None:
                sink.stop()
        except Exception:
            pass
        try:
            if device is not None:
                device.close()
        except Exception:
            pass

    def render(self, maxlen):
        frames = maxlen // 2
        if frames <= 0:
            return b""
        out = array("h")
        append = out.append
        phase = self._phases
        for _ in range(frames):
            self._hum += (self._hum_target - self._hum) * SMOOTHING
            self._hiss += (self._hiss_target - self._hiss) * SMOOTHING
            self._siren += (self._siren_target - self._siren) * SMOOTHING
            self._freq += (self._freq_target - self._freq) * SMOOTHING

            sample = 0.0
            if self._hum > 0.0008:
                inc = self._freq / SAMPLE_RATE
                phase[0] = (phase[0] + inc) % 1.0
                phase[1] = (phase[1] + inc * 2.0) % 1.0
                phase[2] = (phase[2] + inc * 3.02) % 1.0
                tone = _wave(phase[0]) + 0.45 * _wave(phase[1]) + 0.22 * _wave(phase[2])
                sample += self._hum * tone
            if self._hiss > 0.0008:
                raw = random.uniform(-1.0, 1.0)
                filtered = raw - self._noise_prev
                self._noise_prev = raw
                sample += self._hiss * filtered
            if self._siren > 0.0008:
                self._siren_time += 1.0 / SAMPLE_RATE
                high = int(self._siren_time * 2.2) % 2 == 1
                inc = (880.0 if high else 620.0) / SAMPLE_RATE
                phase[3] = (phase[3] + inc) % 1.0
                sample += self._siren * (0.72 * _wave(phase[3]) + 0.28 * _wave((phase[3] * 2.0) % 1.0))
            if self._click_left <= 0 and self._click_queue:
                self._click_amp = self._click_queue.popleft()
                self._click_left = CLICK_FRAMES
            if self._click_left > 0:
                env = self._click_left / CLICK_FRAMES
                self._click_left -= 1
                tick = 1.0 if (self._click_left // 24) % 2 == 0 else -1.0
                sample += self._click_amp * env * env * tick * 0.6
            if sample > 1.0:
                sample = 1.0
            elif sample < -1.0:
                sample = -1.0
            append(int(sample * 32000.0))
        return out.tobytes()
