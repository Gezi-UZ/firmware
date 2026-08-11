# Central configuration — GPIO pins + constants (hardcoded, not sensitive).
# Credentials (WiFi, MQTT, API keys) are loaded from secrets.py (gitignored).
#
# Setup:
#   cp secrets.example.py secrets.py
#   Fill in secrets.py with real values
#   Upload both files to the ESP32 via MicroPico


# ── Load credentials from secrets.py (gitignored) ─────────────────────────
try:
    import secrets as _s
    _WIFI_SSID     = _s.WIFI_SSID
    _WIFI_PASSWORD = _s.WIFI_PASSWORD
    _MQTT_CLUSTER_URL = _s.MQTT_CLUSTER_URL
    _MQTT_PORT     = _s.MQTT_PORT
    _MQTT_USERNAME = _s.MQTT_USERNAME
    _MQTT_PASSWORD = _s.MQTT_PASSWORD
    _API_BASE_URL  = _s.API_BASE_URL
    _DEVICE_ID     = _s.DEVICE_ID
except ImportError:
    # secrets.py missing — warn and use empty defaults so the rest of the
    # code can still import Config without crashing at module load time.
    print("[Config] WARNING: secrets.py not found. Copy secrets.example.py.")
    _WIFI_SSID = _WIFI_PASSWORD = ""
    _MQTT_CLUSTER_URL = ""
    _MQTT_PORT = 8883
    _MQTT_USERNAME = _MQTT_PASSWORD = ""
    _API_BASE_URL = ""
    _DEVICE_ID = "GEZI-ESP32-UNKNOWN"


class Config:
    # ── I2C — LCD 1602 ────────────────────────────────────────
    LCD_SDA  = 21
    LCD_SCL  = 22
    LCD_ADDR = 0x27

    # ── Relay (SRD-05VDC, active-LOW module) ─────────────────
    RELAY_PIN        = 19
    RELAY_ACTIVE_LOW = True

    # ── Status LEDs ───────────────────────────────────────────
    GREEN_PIN = 5   # GPIO 5 — credit active indicator
    RED_PIN   = 4   # GPIO 4 — alert / no-credit indicator

    # ── 4×4 Matrix Keypad ────────────────────────────────────
    # Row pins: R4→R1 (top to bottom on the physical remote)
    ROW_PINS = [26, 27, 14, 0]
    # Column pins: C4→C1 (right to left)
    COL_PINS = [32, 33, 25, 18]
    KEYPAD_MAP = [
        ["1", "2", "3", "A"],
        ["4", "5", "6", "B"],
        ["7", "8", "9", "C"],
        ["*", "0", "#", "D"],
    ]

    # ── PZEM-004T UART ────────────────────────────────────────
    # NOTE: GPIO 16/17 are reserved by PSRAM on ESP32-WROVER.
    # Wire PZEM to unused UART pins if needed.
    PZEM_TX       = 17   # ESP32 TX → PZEM RX
    PZEM_RX       = 16   # ESP32 RX ← PZEM TX
    PZEM_SIMULATE = True  # Set False when physical PZEM is wired

    # ── Backend (loaded from secrets.py) ────────────────────
    API_BASE_URL = _API_BASE_URL
    DEVICE_ID    = _DEVICE_ID

    # ── WiFi (loaded from secrets.py) ────────────────────────
    WIFI_SSID     = _WIFI_SSID
    WIFI_PASSWORD = _WIFI_PASSWORD

    # ── MQTT / HiveMQ Cloud (loaded from secrets.py) ─────────
    MQTT_CLUSTER_URL = _MQTT_CLUSTER_URL
    MQTT_PORT        = _MQTT_PORT
    MQTT_USERNAME = _MQTT_USERNAME
    MQTT_PASSWORD = _MQTT_PASSWORD
    MQTT_USE_TLS  = True   # always TLS for cloud broker

    # ── Business constants ────────────────────────────────────
    WARNING_THRESHOLD_KWH = 5.0   # kWh threshold for WARNING state
    LOOP_MS               = 100   # Main loop delay in milliseconds
