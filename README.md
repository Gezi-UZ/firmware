# Gezi — Firmware IoT (ESP32-WROVER-E)

> **Plataforma Digital Baseada em Internet das Coisas (IoT) para Modernização do Sistema de CREDELEC pela Electricidade de Moçambique**  
> **Autor:** Dai Wen Xuan  
> **Instituição:** Universidade Zambeze — Faculdade de Ciências e Tecnologia (Beira, 2026)

---

## Sobre o Projeto

O **Gezi** é uma solução IoT concebida para modernizar o sistema de pré-pagamento de energia elétrica em Moçambique (**CREDELEC**), gerido pela Electricidade de Moçambique (EDM). 

Este repositório (`gezi-firmware`) contém o código em **MicroPython** e a documentação física da **maquete de simulação / sandbox IoT** executada num microcontrolador **ESP32-WROVER-E**. A maquete simula localmente a medição de energia em kWh, corte e religação de corrente via relé, interface visual no LCD 1602, entrada de códigos/valores via teclado 4x4 e sinalização de estado através de LEDs indicadores.

---

## Componentes de Hardware

* **Microcontrolador:** ESP32-WROVER-E (com SPIRAM/PSRAM)
* **Ecrã:** LCD 1602 com módulo I2C (PCF8574)
* **Atuador:** Módulo de Relé 2 Canais (SRD-05VDC-SL-C, Ativo em nível LOW)
* **Interface de Entrada:** Teclado Matricial 4x4
* **Sinalizadores:** 
  * 1x LED Verde (Indicador de Crédito / Fornecimento Ativo)
  * 1x LED Vermelho (Indicador de Alerta / Sem Crédito)
  * 2x Resistências de $220\Omega$ / $330\Omega$

---

## Mapa de Pinos Completo (GPIOs ESP32-WROVER)

> **Nota Importante de Hardware:** Os pinos **GPIO 16 e 17** são reservados internamente para a memória PSRAM do ESP32 WROVER e **não podem ser utilizados**.

| Componente | Pino do Componente | GPIO ESP32 | Descrição / Função |
|---|---|---|---|
| **LCD 1602 I2C** | SDA | **GPIO 21** | Barramento de dados I2C |
| | SCL | **GPIO 22** | Barramento de relógio I2C |
| | VCC / GND | **5V / GND** | Alimentação do ecrã |
| **Relé 1** | IN1 | **GPIO 19** | Corte / Religação principal de energia |
| **Relé 2** | IN2 | **GPIO 15** | Canal auxiliar / reserva futuro |
| | VCC / GND | **5V / GND** | Alimentação do módulo de relés |
| **LED Vermelho** | Ânodo (+) | **GPIO 4** | Sinalização de alerta/corte (com resistência $220\Omega$) |
| **LED Verde** | Ânodo (+) | **GPIO 5** | Sinalização de crédito ativo (com resistência $220\Omega$) |
| **Teclado 4x4** | Pino 1 (R4) | **GPIO 26** | Linha 4 (`[*, 0, #, D]`) |
| | Pino 2 (R3) | **GPIO 27** | Linha 3 (`[7, 8, 9, C]`) |
| | Pino 3 (R2) | **GPIO 14** | Linha 2 (`[4, 5, 6, B]`) |
| | Pino 4 (R1) | **GPIO 0** | Linha 1 (`[1, 2, 3, A]`) |
| | Pino 5 (C4) | **GPIO 32** | Coluna 4 (`[A, B, C, D]`) |
| | Pino 6 (C3) | **GPIO 33** | Coluna 3 (`[3, 6, 9, #]`) |
| | Pino 7 (C2) | **GPIO 25** | Coluna 2 (`[2, 5, 8, 0]`) |
| | Pino 8 (C1) | **GPIO 18** | Coluna 1 (`[1, 4, 7, *]`) |

---

## Regras de Estado do Sistema

O firmware gere 3 estados principais de fornecimento elétrico consoante o saldo em kWh:

| Condição de Saldo | Mensagem no LCD | Estado do Relé 1 | LED Verde (GPIO 5) | LED Vermelho (GPIO 4) |
|---|:---:|:---:|:---:|:---:|
| **`Saldo == 0.0 kWh`** | **`NO CREDIT`** | **OFF** (Corte) | Apagado | **Aceso Fixo** |
| **`0.0 < Saldo < 5.0 kWh`** | **`WARNING`** | **ON** (Ligado) | **Aceso Fixo** | **Pisca (1000ms)** |
| **`Saldo >= 5.0 kWh`** | **`CREDIT`** | **ON** (Ligado) | **Aceso Fixo** | Apagado |

---

## Mapeamento e Funções do Teclado 4x4

O teclado foi calibrado para permitir introduzir valores decimais e operar a sandbox facilmente:

```text
       [ 1 ] [ 2 ] [ 3 ] [ A ]
       [ 4 ] [ 5 ] [ 6 ] [ B ]
       [ 7 ] [ 8 ] [ 9 ] [ C ]
       [ * ] [ 0 ] [ # ] [ D ]
```

| Tecla Física | Função | Descrição |
|:---:|---|---|
| **`0` a `9`** | Dígitos | Introduz o valor numérico da recarga |
| **`*`** | Ponto Decimal (`.`) | Permite introduzir valores decimais (ex: `12.5` ou `0.5` kWh) |
| **`A`** | **Aceitar (OK)** | Confirma a recarga digitada e atualiza o saldo/relé |
| **`B`** | **Deletar (Backspace)** | Apaga o último dígito introduzido no buffer |
| **`C`** | **Reset kWh** | Zera o saldo para `0.0 kWh` (Simula corte de energia `NO CREDIT`) |
| **`D`** | Reservado | Utilização futura / Navegação |

---

## Estrutura do Repositório

```text
gezi-firmware/
├── boot.py            # Ficheiro de arranque de baixo nível da ESP32
├── i2c_lcd.py         # Driver I2C para o ecrã LCD 1602
├── lcd_api.py         # API abstrata de controlo de carateres do LCD
├── main.py            # Aplicação principal em MicroPython (Controlo de Estados, Relés, LEDs e Teclado)
├── test_keypad.py     # Script de diagnóstico para teste e calibração de matriz do teclado
└── README.md          # Documentação do hardware e firmware
```

---

## Como Executar no ESP32

### 1. Requisitos Prévios
* Placa ESP32-WROVER-E com firmware **MicroPython v1.27.0+** gravado.
* Extensão **MicroPico** (VS Code) ou **Thonny IDE** para transferência de ficheiros.

### 2. Carregar os Ficheiros
Upload de todos os ficheiros Python para a memória flash da ESP32:
* `boot.py`
* `lcd_api.py`
* `i2c_lcd.py`
* `main.py`

### 3. Execução
Para iniciar o sistema na ESP32, executa no REPL:
```python
import main
```
Ou faz reset à placa (botão EN/RST) para arranque automático a partir do `boot.py`.

---

## Contexto Académico

Este repositório faz parte integrante do projeto de fim de curso da **Licenciatura em Engenharia Informática** na **Universidade Zambeze (FCT)**, inserido no ecossistema **Gezi** composto por 4 repositórios:
1. `gezi-mobile`: Aplicação móvel Flutter (Android / iOS)
2. `gezi-firmware`: Firmware IoT MicroPython (este repositório)
3. `gezi-backend`: Servidor REST FastAPI / Python
4. `gezi-infra`: Infraestrutura Docker Compose & MQTT Mosquitto
