# secrets.example.py
# Copiar este ficheiro para "secrets.py" e preencher com os valores reais.
# NOTA: O ficheiro "secrets.py" é ignorado pelo git (.gitignore) para evitar
# que credenciais (passwords, tokens) fiquem expostas publicamente.

WIFI_SSID     = ""
WIFI_PASSWORD = ""

# MQTT (HiveMQ Cloud)
MQTT_CLUSTER_URL = ""
MQTT_PORT        = 8883
MQTT_USERNAME    = ""
MQTT_PASSWORD    = ""

# Backend API
API_BASE_URL  = ""  # Ex: https://gezi-token-service.up.railway.app
DEVICE_ID     = ""  # Ex: GEZI-ESP32-001
DEVICE_ID     = ""  # Ex: GEZI-ESP32-001 (Opcional, pois usa MAC por defeito)

# Contadores Duplos (Números de Série associados no backend)
METER_SERIAL_C0 = "CRD-2026-00001"
METER_SERIAL_C1 = "CRD-2026-00002"

