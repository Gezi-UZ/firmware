# app/adapters/pzem_monitor.py
# Concrete IEnergyMonitor — PZEM-004T UART reader + simulation mode.

import time

from app.domain.ports.i_energy_monitor import IEnergyMonitor
from app.domain.value_objects.energy_reading import EnergyReading


class PzemMonitor(IEnergyMonitor):
    """
    Reads energy data from a PZEM-004T v3.0 sensor over UART (Modbus RTU),
    or falls back to a deterministic simulation for sandbox testing.

    Rate limiting
    -------------
    read() is non-blocking. It polls the sensor at most once every
    READ_INTERVAL_MS (1 second) and returns None in between.

    Simulation mode
    ---------------
    When simulate=True (Config.PZEM_SIMULATE), generates synthetic readings
    at a constant simulated load (_SIM_POWER_W). No UART hardware needed.
    """

    READ_INTERVAL_MS = 1_000   # poll at most once per second
    _SIM_POWER_W     = 100.0   # simulated load in Watts

    # Modbus RTU: read 10 input registers from address 0x01
    _CMD = bytes([0x01, 0x04, 0x00, 0x00, 0x00, 0x0A, 0x70, 0x0D])

    def __init__(self, tx_pin: int, rx_pin: int, simulate: bool = True):
        self._simulate = simulate
        self._last_ms  = 0

        if not simulate:
            from machine import UART
            self._uart = UART(
                2,
                baudrate=9600,
                tx=tx_pin,
                rx=rx_pin,
                timeout=200,
            )

    def read(self):
        """
        Non-blocking. Returns EnergyReading or None.
        Enforces a minimum READ_INTERVAL_MS between actual sensor polls.
        """
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_ms) < self.READ_INTERVAL_MS:
            return None
        self._last_ms = now

        return self._sim_read() if self._simulate else self._uart_read()

    # ── Simulation ────────────────────────────────────────────────────────────

    def _sim_read(self) -> EnergyReading:
        """
        Generate a synthetic reading based on a constant simulated load.
        delta_kwh = (power_W / 1000) × elapsed_hours
        """
        elapsed_h = self.READ_INTERVAL_MS / 3_600_000.0
        delta_kwh = (self._SIM_POWER_W / 1000.0) * elapsed_h
        return EnergyReading(
            voltage_v = 220.0,
            current_a = round(self._SIM_POWER_W / 220.0, 3),
            power_w   = self._SIM_POWER_W,
            delta_kwh = delta_kwh,
        )

    # ── Real UART ─────────────────────────────────────────────────────────────

    def _uart_read(self):
        """Request and parse a PZEM-004T Modbus RTU response."""
        try:
            self._uart.write(self._CMD)
            time.sleep_ms(100)
            raw = self._uart.read(25)
            if raw is None or len(raw) < 25:
                return None
            return self._parse(raw)
        except Exception:
            return None

    @staticmethod
    def _parse(raw: bytes) -> EnergyReading:
        """
        Parse raw PZEM-004T response bytes into an EnergyReading.
        Register layout (Modbus input registers, starting at 0x0000):
          [0] voltage   (×0.1 V)
          [1] current L (×0.001 A, low word)
          [2] current H (×0.001 A, high word)
          [3] power L   (×0.1 W)
          [4] power H
          [5] energy L  (Wh, low word)
          [6] energy H
          [7] frequency (×0.1 Hz)
          [8] power factor (×0.01)
          [9] alarm status
        """
        voltage_v = ((raw[3]  << 8) | raw[4])  / 10.0
        current_a = ((raw[5]  << 8) | raw[6])  / 1000.0
        power_w   = ((raw[7]  << 8) | raw[8])  / 10.0
        # Energy register is cumulative (Wh) — caller should track delta
        energy_wh = ((raw[9]  << 8) | raw[10])
        delta_kwh = energy_wh / 1000.0

        return EnergyReading(
            voltage_v = voltage_v,
            current_a = current_a,
            power_w   = power_w,
            delta_kwh = delta_kwh,
        )
