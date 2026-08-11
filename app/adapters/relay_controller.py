# app/adapters/relay_controller.py
# Concrete IRelay — single channel relay with active-low support.

from machine import Pin

from app.domain.ports.i_relay import IRelay


class RelayController(IRelay):
    """
    Controls one relay channel on the ESP32.

    The SRD-05VDC-SL-C module used in the Gezi maquete is active-LOW:
      - Pin LOW  → relay CLOSED (power flowing)
      - Pin HIGH → relay OPEN   (power cut)

    active_low=True  handles this polarity automatically.
    active_low=False is available for standard active-HIGH modules.
    """

    def __init__(self, pin: int, active_low: bool = True):
        self._pin        = Pin(pin, Pin.OUT)
        self._active_low = active_low
        self._set_relay(False)  # start safe — relay OPEN

    def update(self, meter) -> None:
        """Close relay when meter has credit; open when no credit."""
        self._set_relay(meter.supply_active)

    # ── private ──────────────────────────────────────────────────────────────

    def _set_relay(self, active: bool) -> None:
        """
        Map logical 'active' to the correct pin level for the module polarity.
        """
        if self._active_low:
            self._pin.value(0 if active else 1)
        else:
            self._pin.value(1 if active else 0)
