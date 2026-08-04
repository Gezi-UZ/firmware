# test_keypad.py — Script de Diagnóstico Automático do Teclado 4x4
# pyrefly: ignore [missing-import]
from machine import Pin
import time

# Mapeamento dos 8 pinos do teclado aos GPIOs da ESP32
# Pino 1 ao Pino 8 do conector do teclado:
TECLADO_PINOS = {
    1: 26,
    2: 27,
    3: 14,
    4: 13,
    5: 32,
    6: 33,
    7: 25,
    8: 18,
}

print("=" * 50)
print("  DIAGNÓSTICO AUTOMÁTICO DO TECLADO 4x4")
print("=" * 50)
print("Instruções: Pressiona as teclas (ex: 1, 5, 9, D) uma a uma.")
print("Este script vai identificar a ligação exata dos pinos.\n")

ultimos_pinos = None

while True:
    for pino_out_num, gpio_out in TECLADO_PINOS.items():
        # Define o pino atual como SAÍDA em nível LOW (0)
        p_out = Pin(gpio_out, Pin.OUT)
        p_out.value(0)
        
        # Configura os restantes 7 pinos como ENTRADA com Pull-Up
        for pino_in_num, gpio_in in TECLADO_PINOS.items():
            if pino_in_num == pino_out_num:
                continue
            
            p_in = Pin(gpio_in, Pin.IN, Pin.PULL_UP)
            
            if p_in.value() == 0:
                # Evita imprimir repetidamente a mesma tecla
                par_atual = tuple(sorted([pino_out_num, pino_in_num]))
                if par_atual != ultimos_pinos:
                    print(f"➜ DETETADO: Pino {par_atual[0]} (GPIO {TECLADO_PINOS[par_atual[0]]}) <---> Pino {par_atual[1]} (GPIO {TECLADO_PINOS[par_atual[1]]})")
                    ultimos_pinos = par_atual
                    time.sleep_ms(300)
                break
        
        # Repõe o pino como entrada
        Pin(gpio_out, Pin.IN, Pin.PULL_UP)

    # Limpa o estado quando nenhuma tecla estiver a ser premida
    nenhuma_tecla = True
    for gpio in TECLADO_PINOS.values():
        if Pin(gpio, Pin.IN, Pin.PULL_UP).value() == 0:
            nenhuma_tecla = False
            break
    if nenhuma_tecla:
        ultimos_pinos = None

    time.sleep_ms(20)
