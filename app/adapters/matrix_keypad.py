# app/adapters/matrix_keypad.py
# Concrete IKeypad — 4×4 matrix keypad with software debounce.

from machine import Pin
import time

from app.domain.ports.i_keypad import IKeypad


class MatrixKeypad(IKeypad):
    """
    Scans a 4×4 matrix keypad wired to the ESP32.

    Scan method
    -----------
    Row pins are driven LOW one at a time.
    Column pins are pulled HIGH and read — a LOW reading means that
    key in the active row/column is pressed.

    Debounce
    --------
    A key is reported only once per physical press.
    If the same key is read within DEBOUNCE_MS of the previous report,
    None is returned to suppress the repeat.
    A new press of the *same* key is only registered after the key
    has been released (scan returns None for at least one cycle).
    """

    DEBOUNCE_MS = 50

    def __init__(self, row_pins: list, col_pins: list, keymap: list):
        self._rows = [Pin(p, Pin.OUT, value=1) for p in row_pins]
        self._cols = [Pin(p, Pin.IN, Pin.PULL_UP) for p in col_pins]
        self._keymap    = keymap
        self._last_key  = None   # last reported key
        self._last_ms   = 0      # ticks_ms when last key was reported

    def scan(self):
        """
        Non-blocking scan. Returns key char or None.
        Guarantees at most one event per physical key press.
        """
        key = self._raw_scan()

        if key is None:
            # No key pressed — reset so the same key can fire again
            self._last_key = None
            return None

        now = time.ticks_ms()
        # Suppress if same key and within debounce window
        if (key == self._last_key and
                time.ticks_diff(now, self._last_ms) < self.DEBOUNCE_MS):
            return None

        self._last_key = key
        self._last_ms  = now
        return key

    def _raw_scan(self):
        """Drive each row LOW and read columns. Returns first pressed key."""
        for r_idx, row_pin in enumerate(self._rows):
            row_pin.value(0)
            for c_idx, col_pin in enumerate(self._cols):
                if col_pin.value() == 0:
                    row_pin.value(1)
                    return self._keymap[r_idx][c_idx]
            row_pin.value(1)
        return None
