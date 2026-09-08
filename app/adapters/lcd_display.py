# app/adapters/lcd_display.py
# Concrete IDisplay implementation — 16×2 I2C LCD (HD44780 via PCF8574).

from machine import I2C, Pin
import time

from i2c_lcd import I2cLcd
from app.domain.ports.i_display import IDisplay
from app.domain.entities.meter import NO_CREDIT, WARNING, CREDIT


# ── Error code → localised LCD messages (max 16 chars per line) ──────────────
_ERROR_MAP = {
    "TOKEN_ALREADY_USED": ("JA UTILIZADO",    "TENTE OUTRO"),
    "TOKEN_NOT_FOUND":    ("TOKEN INVALIDO",  "VERIFIQUE"),
    "TOKEN_EXPIRED":      ("TOKEN EXPIRADO",  "PRAZO VENCIDO"),
    "SEM_LIGACAO":        ("SEM LIGACAO",     "WIFI OFFLINE"),
    "DEVICE_NOT_FOUND":   ("DISP. NAO REG.", "CONTACTE EDM"),
    "ERRO_VALIDACAO":     ("ERRO VALIDACAO",  "TENTE NOVAMENTE"),
}
_DEFAULT_ERROR = ("ERRO DESCONHECIDO", "TENTE NOVAMENTE")


class LcdDisplay(IDisplay):
    """
    Drives a 16×2 I2C LCD using the i2c_lcd low-level driver.

    Token entry display layout (20 digits, space every 4, across 2 rows):
      Row 0 — digits  1–10: │XXXX XXXX XX____│
      Row 1 — digits 11–20: │XXXX XXXX XX____│

    The grouping uses a space after every 4th digit within each row,
    giving 12 visible chars + 4 padding underscores per row.
    """

    COLS      = 16
    ROWS      = 2
    MSG_HOLD  = 800   # ms to pause after show_message
    ERR_HOLD  = 2500  # ms to pause after show_error

    def __init__(self, sda_pin: int, scl_pin: int, addr: int = 0x27):
        i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400_000)
        self._lcd = I2cLcd(i2c, addr, self.ROWS, self.COLS)
        self._lcd.backlight_on()

    # ── IDisplay ─────────────────────────────────────────────────────────────

    def show_state(self, meter, meter_c1=None) -> None:
        """
        Normal operating screen.
        If meter_c1 is provided, renders dual meter screen:
          Row 0: C0: 12.34kWh  ON
          Row 1: C1:  0.00kWh OFF
        If only one meter is provided, renders single meter screen.
        """

        if meter_c1 is not None:
            st0 = " ON" if meter.supply_active else "OFF"
            st1 = " ON" if meter_c1.supply_active else "OFF"
            row0 = "C0:{:6.2f}kWh {:>3}".format(meter.balance_kwh, st0)
            row1 = "C1:{:6.2f}kWh {:>3}".format(meter_c1.balance_kwh, st1)
            self._write(row0, row1)
            return

        state = meter.state
        if state == NO_CREDIT:
            row0 = "*** SEM CREDITO *"
            row1 = "  SALDO: 0.000kWh"
        elif state == WARNING:
            row0 = "! AVISO: BAIXO !"
            row1 = "SALDO:{:.3f}kWh".format(meter.balance_kwh)
        else:  # CREDIT
            row0 = "* CREDITO ATIVO *"
            row1 = "SALDO:{:.3f}kWh".format(meter.balance_kwh)

        self._write(row0, row1)

    def show_token_buffer(self, buffer: list) -> None:
        """
        Token entry screen.
        First 10 digits on row 0, last 10 on row 1.
        Groups of 4 separated by spaces; empty positions shown as '_'.

        Example — 14 digits entered ("12345678901234"):
          Row 0: │1234 5678 90____│
          Row 1: │1234 ____ ______│  ← wait, digits 11-14 in second half
        """
        row0 = self._format_token_half(buffer, 0,  10)
        row1 = self._format_token_half(buffer, 10, 20)
        self._write(row0, row1)

    def show_message(self, line1: str, line2: str = "") -> None:
        self._write(
            self._centre(line1),
            self._centre(line2) if line2 else " " * self.COLS,
        )
        time.sleep_ms(self.MSG_HOLD)

    def show_error(self, error_code: str) -> None:
        row0, row1 = _ERROR_MAP.get(error_code, _DEFAULT_ERROR)
        self._write(row0, row1)
        time.sleep_ms(self.ERR_HOLD)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _write(self, row0: str, row1: str) -> None:
        """Low-level: write both rows to the LCD."""
        lcd = self._lcd
        lcd.move_to(0, 0)
        lcd.putstr(row0.ljust(self.COLS)[:self.COLS])
        lcd.move_to(0, 1)
        lcd.putstr(row1.ljust(self.COLS)[:self.COLS])

    def _format_token_half(self, buffer: list, start: int, end: int) -> str:
        """
        Format 10 digits (buffer[start:end]) with a space after every 4th
        digit within this half. Unset positions rendered as '_'.

        Produces a 12-char string (4+1+4+1+2) left-padded to COLS width.

        Example (half 0, digits 0–9, 6 entered):
          buffer = ['1','2','3','4','5','6']
          → "1234 56__ __" → padded → "1234 56__ __    "
        """
        result = []
        for local_i in range(10):
            global_i = start + local_i
            # Insert space before every 4th digit (except position 0)
            if local_i > 0 and local_i % 4 == 0:
                result.append(" ")
            char = buffer[global_i] if global_i < len(buffer) else "_"
            result.append(char)
        return "".join(result).ljust(self.COLS)

    @staticmethod
    def _centre(text: str, width: int = 16) -> str:
        return text[:width].center(width)
