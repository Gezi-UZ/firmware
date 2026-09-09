# app/adapters/lcd_display.py
# Concrete IDisplay implementation — 16×2 I2C LCD (HD44780 via PCF8574).

from machine import I2C, Pin
import time

from i2c_lcd import I2cLcd
from app.domain.ports.i_display import IDisplay
from app.domain.entities.meter import NO_CREDIT, WARNING, CREDIT


# ── Error code → localised LCD messages (max 16 chars per line) ──────────────
_ERROR_MAP = {
    "TOKEN_ALREADY_USED":  ("JA UTILIZADO",    "TENTE OUTRO"),
    "TOKEN_NOT_FOUND":     ("TOKEN INVALIDO",  "VERIFIQUE"),
    "TOKEN_INVALIDO":      ("TOKEN INVALIDO",  "VERIFIQUE"),
    "TOKEN_INVALID_METER": ("CONTADOR ERRADO", "TOKEN OUTRO CONT"),
    "METER_NOT_FOUND":     ("CONTADOR N/ REG", "VERIFIQUE SERIE"),
    "TOKEN_EXPIRED":       ("TOKEN EXPIRADO",  "PRAZO VENCIDO"),
    "SEM_LIGACAO":         ("SEM LIGACAO",     "WIFI OFFLINE"),
    "DEVICE_NOT_FOUND":    ("DISP. NAO REG.", "CONTACTE EDM"),
    "ERRO_VALIDACAO":      ("ERRO VALIDACAO",  "TENTE NOVAMENTE"),
}
_DEFAULT_ERROR = ("ERRO DESCONHECIDO", "TENTE NOVAMENTE")


class LcdDisplay(IDisplay):
    """
    Drives a 16×2 I2C LCD using the i2c_lcd low-level driver.

    Token entry display layout (20 digits, space every 4, across 2 rows):
      Row 0 — digits  1–10: │XXXX XXXX XX____│
      Row 1 — digits 11–20: │XXXX XXXX XX____│
    """

    COLS      = 16
    ROWS      = 2
    MSG_HOLD  = 1200  # ms to pause after show_message (e.g. recharge alert)
    ERR_HOLD  = 2500  # ms to pause after show_error

    def __init__(self, sda_pin: int, scl_pin: int, addr: int = 0x27):
        self._sda_pin = sda_pin
        self._scl_pin = scl_pin
        self._addr = addr
        self._available = False
        self._lcd = None
        self._last_row0 = ""
        self._last_row1 = ""
        self._last_recovery_ms = 0

        try:
            # Use 100 kHz (Standard I2C) for robust communication with PCF8574
            self._i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=100_000)
            time.sleep_ms(50)
            devices = self._i2c.scan()
            hex_devices = [hex(d) for d in devices]
            print(f"[LCD] I2C bus scan (SDA={sda_pin}, SCL={scl_pin}): {hex_devices}")

            if addr in devices:
                self._addr = addr
            elif 0x3F in devices:
                print(f"[LCD] Auto-detected LCD at 0x3F (instead of configured {hex(addr)})")
                self._addr = 0x3F
            elif 0x27 in devices:
                print(f"[LCD] Auto-detected LCD at 0x27 (instead of configured {hex(addr)})")
                self._addr = 0x27
            elif devices:
                print(f"[LCD] Using detected I2C device at {hex(devices[0])}")
                self._addr = devices[0]
            else:
                print(f"[LCD] WARNING: No I2C device found on SDA={sda_pin}, SCL={scl_pin}! Will retry dynamically.")
                return

            self._lcd = I2cLcd(self._i2c, self._addr, self.ROWS, self.COLS)
            self._lcd.backlight_on()
            self._available = True
            print(f"[LCD] Initialized successfully at {hex(self._addr)} (100kHz)")
        except Exception as e:
            print(f"[LCD] Initialization warning: {e} (Display will retry dynamically)")
            self._available = False

    # ── IDisplay ─────────────────────────────────────────────────────────────

    def show_state(self, meter, meter_c1=None) -> None:
        """
        Normal operating screen.
        Deduplicates I2C traffic: only writes when text actually changes.
        """
        if meter_c1 is not None:
            st0 = " ON" if meter.supply_active else "OFF"
            st1 = " ON" if meter_c1.supply_active else "OFF"
            row0 = "C0:{:6.2f}kWh {:>3}".format(meter.balance_kwh, st0)
            row1 = "C1:{:6.2f}kWh {:>3}".format(meter_c1.balance_kwh, st1)
        else:
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

        # Anti-flooding: only write to I2C if display content has changed
        if row0 == self._last_row0 and row1 == self._last_row1 and self._available:
            return

        self._write(row0, row1)

    def show_token_buffer(self, buffer: list) -> None:
        """Token entry screen."""
        self._last_row0 = ""
        self._last_row1 = ""
        row0 = self._format_token_half(buffer, 0,  10)
        row1 = self._format_token_half(buffer, 10, 20)
        self._write(row0, row1)

    def show_message(self, line1: str, line2: str = "") -> None:
        """Shows feedback/notification message and holds for visibility."""
        self._last_row0 = ""
        self._last_row1 = ""
        self._write(
            self._centre(line1),
            self._centre(line2) if line2 else " " * self.COLS,
        )
        time.sleep_ms(self.MSG_HOLD)

    def show_prompt(self, line1: str, line2: str = "") -> None:
        """Immediate prompt render without hold delay."""
        self._last_row0 = ""
        self._last_row1 = ""
        self._write(
            self._centre(line1),
            self._centre(line2) if line2 else " " * self.COLS,
        )

    def show_error(self, error_code: str) -> None:
        self._last_row0 = ""
        self._last_row1 = ""
        row0, row1 = _ERROR_MAP.get(error_code, _DEFAULT_ERROR)
        self._write(row0, row1)
        time.sleep_ms(self.ERR_HOLD)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _write(self, row0: str, row1: str) -> None:
        """Low-level: write both rows to the LCD with fault tolerance and auto-recovery."""
        now = time.ticks_ms()

        # If display is currently unavailable, attempt periodic recovery every 3 seconds
        if not self._available or self._lcd is None:
            if time.ticks_diff(now, self._last_recovery_ms) >= 3000:
                print("[LCD] Attempting to reconnect I2C display...")
                self._recover_i2c()
                if not self._available:
                    return
            else:
                return

        try:
            lcd = self._lcd
            lcd.move_to(0, 0)
            lcd.putstr(self._pad(row0, self.COLS))
            lcd.move_to(0, 1)
            lcd.putstr(self._pad(row1, self.COLS))
            self._last_row0 = row0
            self._last_row1 = row1
        except OSError as e:
            print(f"[LCD] I2C write error ({e}) — attempting recovery...")
            self._recover_i2c()

    def _recover_i2c(self) -> None:
        """Unstick I2C bus and re-detect LCD after I2C glitch or power sag."""
        self._last_recovery_ms = time.ticks_ms()
        try:
            # 1. Unstick I2C bus: clock out SCL 9 times in GPIO mode to release any hung slave
            try:
                scl = Pin(self._scl_pin, Pin.OUT)
                sda = Pin(self._sda_pin, Pin.IN)
                for _ in range(9):
                    scl.value(0)
                    time.sleep_us(5)
                    scl.value(1)
                    time.sleep_us(5)
            except Exception:
                pass

            time.sleep_ms(50)
            # 2. Reset ESP32 hardware I2C peripheral
            self._i2c = I2C(0, sda=Pin(self._sda_pin), scl=Pin(self._scl_pin), freq=100_000)
            time.sleep_ms(50)
            devices = self._i2c.scan()
            print(f"[LCD] I2C recovery scan: {[hex(d) for d in devices]}")

            target_addr = None
            if self._addr in devices:
                target_addr = self._addr
            elif 0x27 in devices:
                target_addr = 0x27
            elif 0x3F in devices:
                target_addr = 0x3F
            elif devices:
                target_addr = devices[0]

            if target_addr is not None:
                self._addr = target_addr
                self._lcd = I2cLcd(self._i2c, self._addr, self.ROWS, self.COLS)
                self._lcd.backlight_on()
                self._available = True
                self._last_row0 = ""
                self._last_row1 = ""
                print(f"[LCD] Successfully recovered I2C LCD at {hex(self._addr)}")
            else:
                self._available = False
                print("[LCD] Recovery scan found no devices. Will retry in 3 seconds.")
        except Exception as e:
            self._available = False
            print(f"[LCD] Recovery error: {e}")

    def _format_token_half(self, buffer: list, start: int, end: int) -> str:
        result = []
        for local_i in range(10):
            global_i = start + local_i
            if local_i > 0 and local_i % 4 == 0:
                result.append(" ")
            char = buffer[global_i] if global_i < len(buffer) else "_"
            result.append(char)
        return self._pad("".join(result), self.COLS)

    @staticmethod
    def _pad(text: str, width: int = 16) -> str:
        """Pad string on the right with spaces up to width (equivalent to ljust)."""
        text = str(text)
        if len(text) < width:
            return text + (" " * (width - len(text)))
        return text[:width]

    @staticmethod
    def _centre(text: str, width: int = 16) -> str:
        """Center string within width without using str.center."""
        text = str(text)[:width]
        pad = width - len(text)
        if pad <= 0:
            return text
        left = pad // 2
        right = pad - left
        return (" " * left) + text + (" " * right)
