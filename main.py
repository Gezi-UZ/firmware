# main.py — Gezi CREDELEC Sandbox — Simulação standalone (sem MQTT)
# ESP32-WROVER-E + LCD I2C 1602 + Teclado 4x4 + Relé (2 canais) + 2 LEDs (Verde/Vermelho)
#
# Regras de Estado:
# - NO CREDIT (saldo == 0.0 kWh): LCD = "NO CREDIT", Relé = OFF, Vermelho = ON fixo, Verde = OFF
# - WARNING   (0 < saldo < 5.0 kWh): LCD = "WARNING", Relé = ON, Verde = ON fixo, Vermelho = Pisca (1000ms)
# - CREDIT    (saldo >= 5.0 kWh): LCD = "CREDIT", Relé = ON, Verde = ON fixo, Vermelho = OFF
from i2c_lcd import I2cLcd
# pyrefly: ignore [missing-import]
from machine import Pin, SoftI2C
import time

# ─────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE HARDWARE
# ─────────────────────────────────────────────────────────
LCD_SDA = 21
LCD_SCL = 22
LCD_ADDR = 0x27

RELAY_MAIN_PIN = 19      # Relé 1 (IN1) — GPIO 19
RELAY_AUX_PIN  = 15      # Relé 2 (IN2) — GPIO 15
RELAY_ACTIVE_LOW = True  # SRD-05VDC-SL-C: LOW liga o relé

RED_LED_PIN   = 4        # LED Vermelho (Alerta / Sem Crédito) — GPIO 4
GREEN_LED_PIN = 5        # LED Verde (Alimentação / Crédito Ativo) — GPIO 5

ROW_PINS = [0, 14, 27, 26]    # R1(Pino 4 -> GPIO 0), R2(Pino 3), R3(Pino 2), R4(Pino 1)
COL_PINS = [18, 25, 33, 32]   # C1(Pino 8), C2(Pino 7), C3(Pino 6), C4(Pino 5)

KEYPAD_MAP = [
    ['1', '4', '7', '.'],
    ['2', '5', '8', '0'],
    ['3', '6', '9', '#'],
    ['A', 'B', 'C', 'D'],
]

# ─────────────────────────────────────────────────────────
# ESTADO SIMULADO
# ─────────────────────────────────────────────────────────
saldo_kwh = 0.0          # começa a 0.0 (NO CREDIT)
buffer_entrada = ""      # dígitos digitados

# Controlo do piscar não-bloqueante do LED Vermelho
BLINK_INTERVAL_MS = 1000
last_blink_time = time.ticks_ms()
red_blink_state = False

# ─────────────────────────────────────────────────────────
# PERIFÉRICOS (LCD, RELÉ, LEDS)
# ─────────────────────────────────────────────────────────
i2c = SoftI2C(scl=Pin(LCD_SCL), sda=Pin(LCD_SDA), freq=400000)
lcd = I2cLcd(i2c, LCD_ADDR, 2, 16)

led_red   = Pin(RED_LED_PIN, Pin.OUT)
led_green = Pin(GREEN_LED_PIN, Pin.OUT)
led_red.value(0)
led_green.value(0)

def relay_set(pin_obj, ligado: bool):
    if RELAY_ACTIVE_LOW:
        pin_obj.value(0 if ligado else 1)
    else:
        pin_obj.value(1 if ligado else 0)

relay_main = Pin(RELAY_MAIN_PIN, Pin.OUT)
relay_aux  = Pin(RELAY_AUX_PIN, Pin.OUT)
relay_set(relay_main, False)
relay_set(relay_aux, False)

# ─────────────────────────────────────────────────────────
# TECLADO 4x4
# ─────────────────────────────────────────────────────────
rows = [Pin(p, Pin.OUT) for p in ROW_PINS]
cols = [Pin(p, Pin.IN, Pin.PULL_UP) for p in COL_PINS]

for r in rows:
    r.value(1)

def ler_tecla():
    for i, r in enumerate(rows):
        r.value(0)
        time.sleep_us(50)
        for j, c in enumerate(cols):
            if c.value() == 0:
                while c.value() == 0:
                    time.sleep_ms(10)
                r.value(1)
                return KEYPAD_MAP[i][j]
        r.value(1)
    return None

# ─────────────────────────────────────────────────────────
# ECRÃ E GESTÃO DE ESTADOS
# ─────────────────────────────────────────────────────────
def actualizar_lcd():
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr("Saldo: {:.1f}kWh".format(saldo_kwh))
    lcd.move_to(0, 1)
    if buffer_entrada:
        lcd.putstr("Codigo: {}".format(buffer_entrada))
    else:
        if saldo_kwh <= 0.0:
            estado = "NO CREDIT"
        elif saldo_kwh < 5.0:
            estado = "WARNING"
        else:
            estado = "CREDIT"
        lcd.putstr(estado)

def atualizar_saidas_e_leds():
    global red_blink_state, last_blink_time

    if saldo_kwh <= 0.0:
        led_green.value(0)
        led_red.value(1)
        relay_set(relay_main, False)

    elif saldo_kwh < 5.0:
        led_green.value(1)
        relay_set(relay_main, True)

        agora = time.ticks_ms()
        if time.ticks_diff(agora, last_blink_time) >= BLINK_INTERVAL_MS:
            red_blink_state = not red_blink_state
            last_blink_time = agora
        led_red.value(1 if red_blink_state else 0)

    else:
        led_green.value(1)
        led_red.value(0)
        relay_set(relay_main, True)

# ─────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────
actualizar_lcd()
atualizar_saidas_e_leds()
print("Gezi sandbox pronto. Sistema iniciado em estado NO CREDIT.")

while True:
    # Atualiza o piscar do LED vermelho continuamente sem bloquear
    atualizar_saidas_e_leds()

    tecla = ler_tecla()
    if tecla is None:
        time.sleep_ms(10)
        continue

    print("Tecla premida:", tecla)

    if tecla.isdigit() or tecla == '.':
        if tecla == '.':
            if '.' not in buffer_entrada and len(buffer_entrada) < 6:
                if not buffer_entrada:
                    buffer_entrada = "0."
                else:
                    buffer_entrada += "."
        else:
            if len(buffer_entrada) < 6:
                buffer_entrada += tecla
        actualizar_lcd()

    elif tecla == 'A':
        # Tecla A: Aceitar recarga (OK)
        if buffer_entrada:
            try:
                valor = float(buffer_entrada)
            except ValueError:
                valor = 0.0
            saldo_kwh += valor
            buffer_entrada = ""
            actualizar_lcd()
            atualizar_saidas_e_leds()
            print("Recarga de {:.1f} kWh aplicada. Novo saldo: {:.1f} kWh".format(valor, saldo_kwh))

    elif tecla == 'B':
        # Tecla B: Deletar último dígito (Backspace)
        if len(buffer_entrada) > 0:
            buffer_entrada = buffer_entrada[:-1]
            actualizar_lcd()

    elif tecla == 'C':
        # Tecla C: Resetar saldo para 0.0 kWh (Simular corte / No Credit)
        saldo_kwh = 0.0
        buffer_entrada = ""
        actualizar_lcd()
        atualizar_saidas_e_leds()
        print("Saldo zerado (Estado NO CREDIT).")

    time.sleep_ms(10)