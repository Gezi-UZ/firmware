# main.py — Composition Root
# Instantiates all concrete adapters and injects them into use-cases.
# Zero business logic lives here.

import time

from app.core.config import Config

# ── Adapters (hardware) ───────────────────────────────────────────────────────
from app.adapters.lcd_display          import LcdDisplay
from app.adapters.matrix_keypad        import MatrixKeypad
from app.adapters.relay_controller     import RelayController
from app.adapters.status_leds          import StatusLeds
from app.adapters.pzem_monitor         import PzemMonitor
from app.adapters.http_token_validator import HttpTokenValidator

from app.adapters.flash_meter_repository   import FlashMeterRepository

# ── Domain ────────────────────────────────────────────────────────────────────
from app.domain.entities.meter import Meter

# ── Use-cases ────────────────────────────────────────────────────────────────
from app.application.use_cases.process_energy_reading import ProcessEnergyReading
from app.application.use_cases.validate_token          import ValidateToken
from app.application.use_cases.handle_keypad_input     import HandleKeypadInput
from app.application.use_cases.update_outputs          import UpdateOutputs
from app.application.use_cases.handle_remote_command   import HandleRemoteCommand

# ── Infrastructure ────────────────────────────────────────────────────────────
from app.infrastructure.wifi import WifiService
from app.infrastructure.mqtt_client import MqttClient


def main() -> None:
    # ── 1. Infrastructure ─────────────────────────────────────────────────────
    wifi = WifiService(Config.WIFI_SSID, Config.WIFI_PASSWORD)
    wifi.connect()  # blocking — must succeed before HTTP calls

    mqtt = MqttClient(
        broker_host=Config.MQTT_CLUSTER_URL,
        device_id=Config.DEVICE_ID,
        port=Config.MQTT_PORT,
        username=Config.MQTT_USERNAME,
        password=Config.MQTT_PASSWORD,
        use_tls=Config.MQTT_USE_TLS
    )

    # ── 2. Adapters ───────────────────────────────────────────────────────────
    display   = LcdDisplay(Config.LCD_SDA, Config.LCD_SCL, Config.LCD_ADDR)
    keypad    = MatrixKeypad(Config.ROW_PINS, Config.COL_PINS, Config.KEYPAD_MAP)
    relay     = RelayController(Config.RELAY_PIN, Config.RELAY_ACTIVE_LOW)
    leds      = StatusLeds(Config.GREEN_PIN, Config.RED_PIN)
    monitor   = PzemMonitor(
        Config.PZEM_TX, Config.PZEM_RX,
        simulate=Config.PZEM_SIMULATE,
    )
    validator = HttpTokenValidator(Config.API_BASE_URL, Config.DEVICE_ID)
    
    # ── 2b. Persistence Adapter
    repo = FlashMeterRepository(filename="meter_state.json", save_threshold_kwh=0.1)

    # ── 3. Domain ─────────────────────────────────────────────────────────────
    # Load state from non-volatile flash memory so we survive reboots
    initial_kwh = repo.load()
    meter = Meter(initial_kwh=initial_kwh)

    # ── 4. Use-cases (dependency injection) ───────────────────────────────────
    uc_energy     = ProcessEnergyReading(monitor, meter, repo)
    uc_validate   = ValidateToken(validator, meter, display, leds, relay, repo)
    uc_keypad     = HandleKeypadInput(keypad, display, uc_validate)
    uc_outputs    = UpdateOutputs(display, leds, relay)
    uc_remote_cmd = HandleRemoteCommand(meter, display, leds, relay, mqtt, repo)

    # Wire up the MQTT callback for remote commands
    mqtt.set_command_callback(uc_remote_cmd.execute)
    mqtt.connect() # Attempt connection to HiveMQ

    # ── 5. Initial render ─────────────────────────────────────────────────────
    uc_outputs.execute(meter)

    # ── 6. Main loop ──────────────────────────────────────────────────────────
    last_telemetry_ms = 0
    TELEMETRY_INTERVAL_MS = 1000  # Send telemetry every 1 second

    while True:
        # A. Process local physical inputs/sensors
        uc_energy.execute()   # deduz consumo medido (ou simulado)
        uc_keypad.execute()   # lê teclado → acumula token → valida se [A]
        
        # B. Process incoming remote commands (from FastAPI via HiveMQ)
        mqtt.check_messages() 
        
        # C. Update physical outputs
        uc_outputs.execute(meter)  # actualiza LCD, LEDs e relé
        
        # D. Publish Telemetry
        now = time.ticks_ms()
        if time.ticks_diff(now, last_telemetry_ms) >= TELEMETRY_INTERVAL_MS:
            mqtt.publish_telemetry(meter) # Pushes state to FastAPI
            last_telemetry_ms = now
            
        time.sleep_ms(Config.LOOP_MS)


main()