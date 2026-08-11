# Gezi Firmware 

Este repositório contém o firmware em **MicroPython** para o medidor de energia pré-pago inteligente do projeto **Gezi**. O firmware foi desenhado utilizando **Clean Architecture** e princípios **SOLID**, separando completamente a lógica de negócio do hardware e garantindo um código altamente testável, escalável e robusto.

---

## Arquitetura do sistema

O firmware adota uma abordagem orientada a eventos (EDA - Event-Driven Architecture) e está dividido em 4 camadas principais:

1. **Domain (`app/domain/`)**: O coração da aplicação. Contém a entidade `Meter` que gere o saldo de kWh e o estado (`CREDIT`, `WARNING`, `NO_CREDIT`). **Nenhum detalhe de hardware (ex: `import machine`) existe aqui.**
2. **Application (`app/application/use_cases/`)**: Regras de negócio orquestradas (ex: gerir o buffer do teclado, pedir validação de tokens, aplicar consumos).
3. **Adapters (`app/adapters/`)**: Onde o software fala com o hardware. Implementações concretas para LCD, Teclado, Relé, PZEM e HTTP. É aqui que os drivers do ESP32 vivem.
4. **Infrastructure (`app/infrastructure/`)**: Serviços de comunicação base, como o cliente WiFi e o cliente MQTT (com suporte a TLS) para comunicar com a Cloud.

O ficheiro `main.py` funciona como **Composition Root**: junta todas as peças e arranca o loop principal, mas não contém lógica de negócio.

---

## Circuito e Ligações (Hardware)

Este projeto foi desenhado para correr num **ESP32** (ex: ESP32-WROVER-E). Aqui estão as ligações padrão configuradas no `app/core/config.py`:

| Componente | Pino ESP32 | Notas / Funcionalidade |
| :--- | :--- | :--- |
| **LCD 1602 (I2C)** | SDA: `21`, SCL: `22` | Mostra o saldo e buffer de 20 dígitos (espaçados a cada 4). |
| **Teclado 4x4** | Linhas: `26`, `27`, `14`, `0` <br> Colunas: `32`, `33`, `25`, `18` | Inserção de tokens. Botão `A` valida, `C` limpa, `B` apaga um dígito. |
| **PZEM-004T (V3.0)**| RX: `16`, TX: `17` | Medição de energia AC (Tensão, Corrente, Potência, kWh). |
| **Módulo Relé (5V)** | PIN: `19` | Corta a corrente quando o saldo chega a 0 kWh (Active-LOW). |
| **LED Verde** | PIN: `5` | Ligado quando há crédito (`CREDIT` e `WARNING`). |
| **LED Vermelho** | PIN: `4` | Pisca (1Hz) no `WARNING` (< 5kWh). Fixo no `NO_CREDIT`. |

> **Nota para testes:** O `PZEM-004T` pode ser simulado alterando `PZEM_SIMULATE = True` no `config.py`. Isto permite testar o decréscimo de saldo na maquete de demonstração sem a necessidade perigosa de usar 220V AC.

---

## Comunicação Cloud (MQTT & FastAPI)

O ESP32 não funciona isolado. Ele é o *Edge Node* numa arquitetura de IoT Cloud:

1. **Recarga via teclado (HTTP POST):** Quando um token de 20 dígitos é inserido, o ESP32 faz um pedido síncrono ao backend FastAPI para validação (hashing/idempotência contra o Supabase). O ESP32 **nunca** valida tokens localmente.
2. **Telemetria (MQTT):** A cada segundo, o ESP32 publica o seu saldo e consumos para o HiveMQ Cloud no tópico `gezi/{device_id}/telemetry`.
3. **Recarga remota (MQTT):** O ESP32 subscreve ao tópico `gezi/{device_id}/cmd/credit`. Se o utilizador comprar energia via Mobile App (Flutter), o FastAPI avisa o ESP32 instantaneamente via HiveMQ, o ESP32 adiciona o crédito e acende o LCD a dizer "RECARGA REMOTA".

---

## Como configurar e instalar (Setup)

1. **Instalar o MicroPython:** Certifica-te que tens o firmware do MicroPython "flashado" no teu ESP32.
2. **Configurar as credenciais (Secrets):**
   * Copia o ficheiro template de credenciais:
     ```bash
     cp secrets.example.py secrets.py
     ```
   * Abre o `secrets.py` e preenche os teus dados de WiFi e as tuas credenciais do **HiveMQ Cloud** (Username, Password).
   * *O `secrets.py` é ignorado pelo Git (via `.gitignore`) para não expores as tuas passwords acidentalmente.*
3. **Enviar para o ESP32:**
   * Usa a extensão **MicroPico** no VSCode ou a app **Thonny** para enviar todos os ficheiros da pasta atual (incluindo as sub-pastas `app/` e o teu novo `secrets.py`) para a raiz do ESP32.
   * O ESP32 irá executar o `main.py` automaticamente no boot.

---
*Projeto Académico — Licenciatura em Engenharia Informática, Universidade Zambeze (FCT).*
