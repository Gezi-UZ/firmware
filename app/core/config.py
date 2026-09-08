# Central configuration — GPIO pins + constants (hardcoded, not sensitive).
# Credentials (WiFi, MQTT, API keys) are loaded from secrets.py (gitignored).
#
# Setup:
#   cp secrets.example.py secrets.py
#   Fill in secrets.py with real values
#   Upload both files to the ESP32 via MicroPico


# ── Load credentials from secrets.py (gitignored) ─────────────────────────
# ── Load credentials from config.json (priority) or secrets.py (fallback) ───
_config_json = {}
try:
    try:
        # pyrefly: ignore [missing-import]
        import ujson as _json
    except ImportError:
        import json as _json
    with open("config.json", "r") as _f:
        _config_json = _json.load(_f)
except Exception:
    _config_json = {}

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
    _s = None

_WIFI_SSID = _config_json.get("wifi_ssid", getattr(_s, "WIFI_SSID", ""))
_WIFI_PASSWORD = _config_json.get("wifi_pass", getattr(_s, "WIFI_PASSWORD", ""))
_MQTT_CLUSTER_URL = _config_json.get("mqtt_broker", getattr(_s, "MQTT_CLUSTER_URL", ""))
_MQTT_PORT = int(_config_json.get("mqtt_port", getattr(_s, "MQTT_PORT", 8883)))
_MQTT_USERNAME = _config_json.get("mqtt_user", getattr(_s, "MQTT_USERNAME", ""))
_MQTT_PASSWORD = _config_json.get("mqtt_pass", getattr(_s, "MQTT_PASSWORD", ""))
_METER_SERIAL_C0 = _config_json.get("meter_serial_c0", getattr(_s, "METER_SERIAL_C0", "CRD-2026-00001"))
_METER_SERIAL_C1 = _config_json.get("meter_serial_c1", getattr(_s, "METER_SERIAL_C1", "CRD-2026-00002"))
_API_BASE_URL = _config_json.get("api_base_url", getattr(_s, "API_BASE_URL", ""))
_DEVICE_ID = _config_json.get("device_id", getattr(_s, "DEVICE_ID", "GEZI-ESP32-UNKNOWN"))

if not _s and not _config_json:
    print("[Config] WARNING: Neither config.json nor secrets.py found. Using defaults.")


class Config:
    # ── I2C — LCD 1602 ────────────────────────────────────────
    LCD_SDA  = 21
    LCD_SCL  = 22
    LCD_ADDR = 0x27

    # ── Relay (SRD-05VDC, active-LOW module) ─────────────────
    RELAY_PIN        = 19
    # ── 2-Channel Relay Module (SRD-05VDC, active-LOW) ─────────
    # IN1 on 2-relay module -> GPIO 19 (Channel 0)
    # IN2 on 2-relay module -> GPIO 15 (Channel 1)
    RELAY_PIN        = 19   # Backwards compatibility
    RELAY_PIN_C0     = 19   # IN1 -> Canal 0
    RELAY_PIN_C1     = 15   # IN2 -> Canal 1
    RELAY_ACTIVE_LOW = True

    # ── Status LEDs ───────────────────────────────────────────
    GREEN_PIN = 5   # GPIO 5 — credit active indicator
    RED_PIN   = 4   # GPIO 4 — alert / no-credit indicator
    STATUS_LED_TIMER_ID = 0  # ESP32 hardware timer (0..3)

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
    # ── Meter Serials (Dual Channel) ──────────────────────────
    METER_SERIAL_C0 = _METER_SERIAL_C0
    METER_SERIAL_C1 = _METER_SERIAL_C1

    # ── Backend ───────────────────────────────────────────────
    API_BASE_URL = _API_BASE_URL
    DEVICE_ID    = _DEVICE_ID

    # ── WiFi (loaded from secrets.py) ────────────────────────
    # ── WiFi ──────────────────────────────────────────────────
    WIFI_SSID     = _WIFI_SSID
    WIFI_PASSWORD = _WIFI_PASSWORD

    # ── MQTT / HiveMQ Cloud ───────────────────────────────────
    MQTT_CLUSTER_URL = _MQTT_CLUSTER_URL
    MQTT_PORT        = _MQTT_PORT
    MQTT_USERNAME    = _MQTT_USERNAME
    MQTT_PASSWORD    = _MQTT_PASSWORD
    MQTT_USE_TLS     = True   # always TLS for cloud broker (port 8883)

    # ── Business constants ────────────────────────────────────
    WARNING_THRESHOLD_KWH = 5.0    # kWh threshold for WARNING state
    LOOP_MS               = 100    # Main loop delay in milliseconds
    TELEMETRY_INTERVAL_MS = 30000  # Telemetry interval (30s as per guide)
    FIRMWARE_VERSION      = "v1.2.0-dual"

    @classmethod
    def save_meter_serials(cls, serial_c0: str, serial_c1: str) -> bool:
        """Persists meter serial numbers into config.json for future boots."""
        try:
            try:
                import ujson as _json
            except ImportError:
                import json as _json

            data = {}
            try:
                with open("config.json", "r") as f:
                    data = _json.load(f)
            except Exception:
                data = {}

            data["meter_serial_c0"] = str(serial_c0).strip()
            data["meter_serial_c1"] = str(serial_c1).strip()

            with open("config.json", "w") as f:
                _json.dump(data, f)

            cls.METER_SERIAL_C0 = str(serial_c0).strip()
            cls.METER_SERIAL_C1 = str(serial_c1).strip()
            return True
        except Exception as e:
            print("[Config] Error saving config.json:", e)
            return False
