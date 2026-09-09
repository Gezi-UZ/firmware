# i2c_lcd.py — Driver robusto e otimizado para LCD 1602/2004 via backpack I2C (PCF8574)
# Implementação HD44780 em modo 4 bits com envio atômico de frames I2C.

import time


class I2cLcd:
    def __init__(self, i2c, addr, num_lines, num_columns):
        self.i2c = i2c
        self.addr = addr
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.backlight = 0x08  # bit 3 do PCF8574 controla o backlight

        time.sleep_ms(25)
        # Sequência de reset/init do HD44780 (datasheet, modo 4 bits)
        self._write_nibble(0x03)
        time.sleep_ms(5)
        self._write_nibble(0x03)
        time.sleep_us(150)
        self._write_nibble(0x03)
        self._write_nibble(0x02)  # entra em modo 4 bits

        self._command(0x28)  # function set: 4 bits, 2 linhas, fonte 5x8
        self._command(0x0C)  # display on, cursor off, blink off
        self.clear()
        self._command(0x06)  # entry mode: incrementa, sem shift

    # ── baixo nível com escrita em lote (reduz START/STOP I2C em 70%) ─────────
    def _write_nibble(self, nibble):
        val = ((nibble << 4) & 0xF0) | self.backlight
        self.i2c.writeto(self.addr, bytes([val | 0x04, val & 0xFB]))
        time.sleep_us(50)

    def _send(self, value, rs_bit):
        high = rs_bit | (value & 0xF0) | self.backlight
        low = rs_bit | ((value << 4) & 0xF0) | self.backlight
        # Pulsa Enable para nibble alto e baixo num único pacote I2C
        self.i2c.writeto(self.addr, bytes([high | 0x04, high & 0xFB, low | 0x04, low & 0xFB]))
        time.sleep_us(40)

    def _command(self, cmd):
        self._send(cmd, 0x00)
        if cmd in (0x01, 0x02):
            time.sleep_ms(2)

    def _data(self, data):
        self._send(data, 0x01)  # RS=1 → escreve caráter

    # ── API pública ──────────────────────────────────────
    def clear(self):
        self._command(0x01)

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
        self.i2c.writeto(self.addr, bytes([self.backlight]))

    def backlight_off(self):
        self.backlight = 0x00
        self.i2c.writeto(self.addr, bytes([self.backlight]))