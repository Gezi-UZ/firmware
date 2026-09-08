# main.py — Composition Root
# Instantiates all concrete adapters and injects them into use-cases.
# Orchestrates Dual-Channel Meters (Channel 0 & Channel 1), HiveMQ TLS with SNI,
# Auto-Discovery (Hello), Remote Commands (APPLY_CREDITS with ACK), and continuous telemetry.
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
    print("=" * 50)
    print("  GEZI IOT FIRMWARE — DUAL-CHANNEL METER")
    print(f"  Version: {Config.FIRMWARE_VERSION}")
    print("=" * 50)

    # ── 1. Infrastructure (WiFi & Identification) ─────────────────────────────
    wifi = WifiService(Config.WIFI_SSID, Config.WIFI_PASSWORD)
    wifi_ok = wifi.connect()  # Attempt connection

    mac = wifi.get_mac_address()
    ip = wifi.get_ip()
    print(f"[Boot] MAC Address : {mac}")
    print(f"[Boot] IP Address  : {ip}")
    print(f"[Boot] Meter C0    : {Config.METER_SERIAL_C0}")
    print(f"[Boot] Meter C1    : {Config.METER_SERIAL_C1}")

    # ── 2. Adapters & Persistence ─────────────────────────────────────────────
    display  = LcdDisplay(Config.LCD_SDA, Config.LCD_SCL, Config.LCD_ADDR)
    keypad   = MatrixKeypad(Config.ROW_PINS, Config.COL_PINS, Config.KEYPAD_MAP)

    # 2-channel Relay Module: IN1 -> GPIO 19 (C0), IN2 -> GPIO 15 (C1)
    relay_c0 = RelayController(Config.RELAY_PIN_C0, Config.RELAY_ACTIVE_LOW)
    relay_c1 = RelayController(Config.RELAY_PIN_C1, Config.RELAY_ACTIVE_LOW)

    leds     = StatusLeds(Config.GREEN_PIN, Config.RED_PIN, Config.STATUS_LED_TIMER_ID)
    monitor  = PzemMonitor(
        Config.PZEM_TX, Config.PZEM_RX,
        simulate=Config.PZEM_SIMULATE,
    )
    validator = HttpTokenValidator(Config.API_BASE_URL, mac)

    # Separate Flash repositories for independent wear-leveling per channel
    repo_c0 = FlashMeterRepository(filename="meter_state_c0.json", save_threshold_kwh=0.1)
    repo_c1 = FlashMeterRepository(filename="meter_state_c1.json", save_threshold_kwh=0.1)

    # ── 3. Domain Entities ────────────────────────────────────────────────────
    initial_kwh_c0 = repo_c0.load()
    meter_c0 = Meter(initial_kwh=initial_kwh_c0, serial_number=Config.METER_SERIAL_C0, channel=0)

    initial_kwh_c1 = repo_c1.load()
    meter_c1 = Meter(initial_kwh=initial_kwh_c1, serial_number=Config.METER_SERIAL_C1, channel=1)

    # ── 4. MQTT Client (HiveMQ Cloud TLS 8883) ────────────────────────────────
    mqtt = MqttClient(
        broker_host=Config.MQTT_CLUSTER_URL,
        client_id=mac,
        port=Config.MQTT_PORT,
        username=Config.MQTT_USERNAME,
        password=Config.MQTT_PASSWORD,
        use_tls=Config.MQTT_USE_TLS,
        meter_serial_c0=Config.METER_SERIAL_C0,
        meter_serial_c1=Config.METER_SERIAL_C1
    )

    # ── 5. Use-cases (Dependency Injection) ───────────────────────────────────
    uc_energy     = ProcessEnergyReading(monitor, meter_c0, repo_c0, meter_c1, repo_c1)
    uc_validate   = ValidateToken(validator, meter_c0, display, leds, relay_c0, repo_c0)
    uc_keypad     = HandleKeypadInput(keypad, display, uc_validate)
    uc_outputs    = UpdateOutputs(display, leds, relay_c0, relay_c1)
    uc_remote_cmd = HandleRemoteCommand(
        meter_c0=meter_c0, relay_c0=relay_c0, repo_c0=repo_c0,
        display=display, leds=leds, mqtt_client=mqtt,
        meter_c1=meter_c1, relay_c1=relay_c1, repo_c1=repo_c1
    )

    def on_device_config(payload: dict) -> None:
        c0 = str(payload.get("meter_serial_c0") or payload.get("c0") or "").strip()
        c1 = str(payload.get("meter_serial_c1") or payload.get("c1") or "").strip()

        updated = False
        if c0 and c0 != meter_c0.serial_number:
            print(f"[Provisioning] Canal 0 serial updated: {meter_c0.serial_number} -> {c0}")
            meter_c0.serial_number = c0
            updated = True

        if c1 and c1 != meter_c1.serial_number:
            print(f"[Provisioning] Canal 1 serial updated: {meter_c1.serial_number} -> {c1}")
            meter_c1.serial_number = c1
            updated = True

        if updated:
            Config.save_meter_serials(meter_c0.serial_number, meter_c1.serial_number)
            mqtt.update_meter_serials(meter_c0.serial_number, meter_c1.serial_number)
            print(f"[Provisioning] Serials saved to config.json: C0={meter_c0.serial_number}, C1={meter_c1.serial_number}")

    # Wire up the MQTT callbacks for remote commands & dynamic device configuration
    mqtt.set_command_callback(uc_remote_cmd.execute)
    mqtt.set_config_callback(on_device_config)

    # Connect to HiveMQ Cloud & announce presence (Hello)
    if wifi_ok and mqtt.connect():
        mqtt.publish_hello(mac, ip, firmware=Config.FIRMWARE_VERSION)

    # ── 6. Initial render ─────────────────────────────────────────────────────
    uc_outputs.execute(meter_c0, meter_c1)

    # ── 7. Main loop ──────────────────────────────────────────────────────────
    last_telemetry_ms = 0

    while True:
        now = time.ticks_ms()

        # A. Process local physical inputs and sensor consumption
        uc_energy.execute()   # deducts consumption on active channels
        uc_keypad.execute()   # scans keypad -> accumulates token -> validates if [A]

        # B. Process incoming remote commands (from FastAPI via HiveMQ)
        mqtt.check_messages()

        # B2. Resilient auto-reconnection if network dropped
        mqtt.reconnect_if_needed(now, interval_ms=10000)

        # C. Update physical outputs (Display dual channels, Relays, LEDs)
        uc_outputs.execute(meter_c0, meter_c1)

        # D. Publish Continuous Telemetry (every 30s as specified in guide)
        if time.ticks_diff(now, last_telemetry_ms) >= Config.TELEMETRY_INTERVAL_MS:
            if mqtt.is_connected:
                if meter_c0.serial_number:
                    mqtt.publish_telemetry(
                        serial=meter_c0.serial_number,
                        kwh_saldo=meter_c0.balance_kwh,
                        relay_state=relay_c0.is_active,
                        reading=uc_energy.last_reading_c0
                    )
                if meter_c1.serial_number:
                    mqtt.publish_telemetry(
                        serial=meter_c1.serial_number,
                        kwh_saldo=meter_c1.balance_kwh,
                        relay_state=relay_c1.is_active,
                        reading=uc_energy.last_reading_c1
                    )
            last_telemetry_ms = now

        time.sleep_ms(Config.LOOP_MS)


if __name__ == "__main__":
    main()