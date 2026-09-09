# i2c_lcd.py — Driver para LCD 1602/2004 via backpack I2C (PCF8574)
# Implementação canónica do protocolo HD44780 em modo 4 bits para MicroPython.
# Uso: from i2c_lcd import I2cLcd
#      lcd = I2cLcd(i2c, 0x27, 2, 16)

import time


class I2cLcd:
    def __init__(self, i2c, addr, num_lines, num_columns):
        self.i2c = i2c
        self.addr = addr
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.backlight = 0x08  # bit 3 do PCF8574 controla o backlight (0x08 = ligado)

        time.sleep_ms(20)
        # Sequência canónica de inicialização do HD44780 (datasheet, modo 4 bits)
        self._write_nibble(0x03)
        time.sleep_ms(5)
        self._write_nibble(0x03)
        time.sleep_us(150)
        self._write_nibble(0x03)
        self._write_nibble(0x02)  # Entra formalmente em modo 4 bits

        self._command(0x28)  # Function set: 4 bits, 2 linhas, fonte 5x8
        self._command(0x0C)  # Display ON, cursor OFF, blink OFF
        self.clear()
        self._command(0x06)  # Entry mode: incrementa cursor, sem scroll

    # ── Baixo nível ─────────────────────────────────────────────────────────

    def _write_byte(self, data):
        self.i2c.writeto(self.addr, bytes([data | self.backlight]))

    def _pulse_enable(self, data):
        self._write_byte(data | 0x04)   # E = 1
        time.sleep_us(1)
        self._write_byte(data & ~0x04)  # E = 0
        time.sleep_us(50)

    def _write_nibble(self, nibble):
        data = (nibble << 4) & 0xF0
        self._write_byte(data)
        self._pulse_enable(data)

    def _send(self, value, rs_bit):
        high = rs_bit | (value & 0xF0)
        low = rs_bit | ((value << 4) & 0xF0)
        self._write_byte(high)
        self._pulse_enable(high)
        self._write_byte(low)
        self._pulse_enable(low)

    def _command(self, cmd):
        self._send(cmd, 0x00)
        if cmd in (0x01, 0x02):
            time.sleep_ms(2)

    def _data(self, data):
        self._send(data, 0x01)

    # ── API pública ─────────────────────────────────────────────────────────

    def clear(self):
        self._command(0x01)
        time.sleep_ms(2)

    def move_to(self, col, row):
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row >= len(row_offsets):
            row = 0
        self._command(0x80 | (col + row_offsets[row]))

    def putstr(self, string):
        for ch in string:
            if ch == '\n':
                continue
            self._data(ord(ch))

    def backlight_on(self):
        self.backlight = 0x08
        self._write_byte(0x00)

    def backlight_off(self):
        self.backlight = 0x00
        self._write_byte(0x00)