# Guia de Integração IoT: ESP32 (MicroPython) ↔ HiveMQ ↔ Backend

Este documento detalha o que precisa de ser implementado no firmware (MicroPython) do ESP32 para que este comunique correctamente com a nova arquitectura da infraestrutura (Backend FastAPI + HiveMQ), suportando o sistema de **Contadores Duplos** (dois relés/canais por ESP32).

---

## 1. O Fluxo de Comunicação (Visão Geral)

O ESP32 actua como um *Edge Node* que gere fisicamente dois contadores (Canal 0 e Canal 1). O ciclo de vida da comunicação é o seguinte:

1. **Boot & WiFi**: Liga-se à rede Wi-Fi.
2. **Conexão MQTT**: Liga-se ao HiveMQ Cloud usando TLS (Porta 8883).
3. **Auto-Discovery (Hello)**: Publica o seu endereço MAC para o backend o registar automaticamente como um `Módulo IoT`.
4. **Subscrição de Comandos**: Subscreve aos tópicos MQTT de comandos dos seus dois contadores associados para receber recargas ou ordens de corte.
5. **Telemetria Contínua**: A cada *N* segundos, lê os sensores PZEM-004T e publica o consumo (kWh) e o estado dos relés para o backend.
6. **Confirmação (ACK)**: Sempre que processa um comando (ex: recarga), envia um ACK (Acknowledge) de volta.

---

## 2. Requisitos e Configuração Inicial (MicroPython)

### 2.1. Bibliotecas Necessárias
Garante que tens as seguintes bibliotecas no ESP32:
- `umqtt.simple` ou `umqtt.robust` (para o cliente MQTT).
- `machine`, `network`, `ubinascii` (nativas).
- `json` e `time` (nativas).

### 2.2. Obtenção do MAC Address
O MAC Address é fundamental para o **Auto-Discovery**. Em MicroPython, obtém-se assim:

```python
import network
import ubinascii

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac = ubinascii.hexlify(wlan.config('mac'), ':').decode()
# Resultado: "ec:60:04:xx:yy:zz"
```

### 2.3. Ficheiro de Configuração (`config.json`)
O ESP32 precisa de saber quais são os **Números de Série** dos dois contadores que ele controla (para poder publicar nos tópicos correctos da API). Recomenda-se um `config.json` no ESP32:

```json
{
  "wifi_ssid": "A_TUA_REDE",
  "wifi_pass": "A_TUA_PASSWORD",
  "mqtt_broker": "xxxx.s1.eu.hivemq.cloud",
  "mqtt_user": "teu_user_hivemq",
  "mqtt_pass": "tua_pass_hivemq",
  "meter_serial_c0": "CRD-2026-00001",
  "meter_serial_c1": "CRD-2026-00002"
}
```

---

## 3. Implementação MQTT

### 3.1. Conexão Segura ao HiveMQ (TLS)
O HiveMQ exige TLS. Em MicroPython, a conexão faz-se passando `ssl=True`.

```python
from umqtt.simple import MQTTClient
import ssl

def connect_mqtt(client_id, server, user, password):
    client = MQTTClient(
        client_id=client_id,
        server=server,
        port=8883,
        user=user,
        password=password,
        keepalive=60,
        ssl=True,
        ssl_params={'server_hostname': server}
    )
    client.set_callback(mqtt_callback)
    client.connect()
    print("Conectado ao HiveMQ!")
    return client
```

### 3.2. Passo 1: Auto-Discovery (Hello)
Assim que conecta, o ESP32 **deve** anunciar a sua presença para que o backend crie o dispositivo na tabela `dispositivo_iot` (se for novo) ou actualize o estado.

**Tópico:** `gezi/v1/{mac_address}/hello`

```python
def publish_hello(client, mac_address):
    topic = f"gezi/v1/{mac_address}/hello"
    payload = {
        "firmware": "v1.2.0-dual",
        "ip": wlan.ifconfig()[0]
    }
    client.publish(topic, json.dumps(payload), qos=1)
    print(f"Enviado Hello no tópico: {topic}")
```

### 3.3. Passo 2: Subscrever a Comandos (CMD)
O ESP32 deve ouvir comandos enviados pelo backend (ex: recargas). Como ele tem 2 canais, deve subscrever aos tópicos dos 2 números de série.

**Tópicos a subscrever:**
- `credelec/meter/{meter_serial_c0}/cmd`
- `credelec/meter/{meter_serial_c1}/cmd`

```python
def subscribe_to_commands(client, serial_c0, serial_c1):
    client.subscribe(f"credelec/meter/{serial_c0}/cmd", qos=1)
    client.subscribe(f"credelec/meter/{serial_c1}/cmd", qos=1)
    print("Subscrito aos comandos dos canais 0 e 1")
```

### 3.4. Passo 3: Receber e Processar Comandos (Callback)
Quando cai um pagamento via M-Pesa, o backend envia uma mensagem para aplicar créditos (`APPLY_CREDITS`). O ESP32 intercepta e actualiza o saldo.

```python
def mqtt_callback(topic, msg):
    topic = topic.decode()
    payload = json.loads(msg.decode())
    
    print(f"Recebido em {topic}: {payload}")
    
    # Descobrir para qual contador é o comando
    serial = topic.split("/")[2] # Extrai 'CRD-2026-00001' do tópico
    
    if payload.get("command") == "APPLY_CREDITS":
        kwh_adicionado = payload.get("kwh", 0.0)
        command_id = payload.get("command_id", "desconhecido")
        
        # 1. Adicionar kwh ao contador correcto (Lógica interna)
        if serial == config["meter_serial_c0"]:
            adicionar_saldo_canal_0(kwh_adicionado)
        elif serial == config["meter_serial_c1"]:
            adicionar_saldo_canal_1(kwh_adicionado)
            
        # 2. Ligar o relé se o saldo > 0
        verificar_reles()
        
        # 3. Enviar ACK para confirmar ao backend
        publish_ack(client, serial, command_id, "ACK", kwh_adicionado)
```

### 3.5. Passo 4: Enviar Confirmação (ACK)
O backend (módulo `iot/ack`) precisa saber que a recarga foi aplicada no hardware, caso contrário fará retry ou fará o reembolso do M-Pesa ao cliente.

**Tópico:** `credelec/meter/{serial}/ack`

```python
def publish_ack(client, serial, command_id, status, applied_kwh):
    topic = f"credelec/meter/{serial}/ack"
    payload = {
        "command_id": command_id,
        "status": status,
        "applied_kwh": applied_kwh
    }
    client.publish(topic, json.dumps(payload), qos=1)
```

### 3.6. Passo 5: Enviar Telemetria Contínua
A cada X segundos (ex: 30s), o ESP32 lê os sensores e envia o estado para actualizar a app Mobile (via Supabase Realtime).

**Tópicos:**
- `credelec/meter/{meter_serial_c0}/telemetry`
- `credelec/meter/{meter_serial_c1}/telemetry`

```python
def publish_telemetry(client, serial, kwh_saldo, relay_state):
    topic = f"credelec/meter/{serial}/telemetry"
    # Campos baseados na Documentação da API
    payload = {
        "kwh": round(kwh_saldo, 2),
        "relay": relay_state,
        # Opcionais lidos do PZEM
        # "voltage": 220.4,
        # "current": 2.31,
        # "power_w": 509.0 
    }
    client.publish(topic, json.dumps(payload), qos=0)
```

---

## 4. Loop Principal (Resumo)

O `main.py` do MicroPython deve orquestrar tudo isto de forma assíncrona ou gerindo temporizadores (`time.ticks_ms()`).

```python
# Pseudo-código do Loop Principal
def main():
    mac = obter_mac()
    client = connect_mqtt(client_id=mac, ...)
    
    publish_hello(client, mac)
    subscribe_to_commands(client, config["meter_serial_c0"], config["meter_serial_c1"])
    
    last_telemetry = time.ticks_ms()
    
    while True:
        # 1. Manter a conexão e verificar mensagens (comandos pendentes)
        client.check_msg()
        
        # 2. Ler sensores (PZEM) e decrementar saldo consoante o consumo
        ler_sensores_e_reduzir_saldo()
        verificar_reles() # Desliga se saldo <= 0
        
        # 3. Enviar telemetria a cada 30 segundos
        if time.ticks_diff(time.ticks_ms(), last_telemetry) > 30000:
            publish_telemetry(client, config["meter_serial_c0"], saldo_c0, rele_c0)
            publish_telemetry(client, config["meter_serial_c1"], saldo_c1, rele_c1)
            last_telemetry = time.ticks_ms()
            
        time.sleep(0.1)

if __name__ == "__main__":
    main()
```

## 5. Notas Importantes

1. **Gestão de Perda de Ligação (QoS):** Se a rede falhar, o ESP32 continuará a decrementar o saldo localmente e a desligar os relés se a energia acabar. Quando a rede voltar, o cliente MQTT deve reconectar-se (usar blocos `try/except` no `.check_msg()` e no `.publish()`) e publicar o saldo actualizado.
2. **HMAC (Segurança Avançada):** Se o firmware implementar validação HMAC, lembre-se de importar o módulo `uhashlib` e `hmac` (pode requerer compilação no MicroPython) para validar a assinatura enviada no payload dos comandos. Caso contrário, para testes, ignore o campo `hmac`.
