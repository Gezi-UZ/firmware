# app/adapters/status_leds.py
# Concrete ILeds — green/red status LEDs with hardware Timer blink.

from machine import Pin, Timer

from app.domain.ports.i_leds import ILeds
from app.domain.entities.meter import NO_CREDIT, WARNING, CREDIT


class StatusLeds(ILeds):
    """
    Drives the green and red status LEDs.

    State → LED behaviour:
      CREDIT    → green ON,  red OFF
      WARNING   → green ON,  red BLINK 1 Hz (via hardware Timer — non-blocking)
      NO_CREDIT → green OFF, red ON (solid)

    A hardware Timer is used for blinking so the main loop is never stalled.
    The Timer is deinitialised when leaving WARNING state to prevent
    spurious interrupts.
    """

    BLINK_FREQ_HZ = 1   # 1 Hz blink → LED on 500 ms / off 500 ms

    def __init__(self, green_pin: int, red_pin: int, timer_id: int = 0):
        self._green = Pin(green_pin, Pin.OUT, value=0)
        self._red   = Pin(red_pin,   Pin.OUT, value=0)
        self._timer = Timer(timer_id)         # Hardware timer (ESP32 supports IDs 0..3)
        self._blinking      = False
        self._current_state = None        # track last state to skip redundant work

    def update(self, meter) -> None:
        state = meter.state
        if state == self._current_state:
            return  # nothing changed — skip Timer restarts

        self._current_state = state
        self._stop_blink()

        if state == CREDIT:
            self._green.value(1)
            self._red.value(0)

        elif state == WARNING:
            self._green.value(1)
            self._start_blink()

        else:  # NO_CREDIT
            self._green.value(0)
            self._red.value(1)

    # ── private ──────────────────────────────────────────────────────────────

    def _start_blink(self) -> None:
        self._blinking = True
        # freq × 2 because each callback invocation toggles (half-period)
        self._timer.init(
            freq=self.BLINK_FREQ_HZ * 2,
            mode=Timer.PERIODIC,
            callback=self._toggle_red,
        )

    def _stop_blink(self) -> None:
        if self._blinking:
            self._timer.deinit()
            self._blinking = False
        self._red.value(0)  # ensure red is off after stopping

    def _toggle_red(self, _t) -> None:
        """Timer ISR — toggles the red LED."""
        self._red.value(not self._red.value())
