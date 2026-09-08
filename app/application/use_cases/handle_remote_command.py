# Use-case: Handles incoming MQTT commands from the backend.
# Use-case: Handles incoming MQTT commands from the backend for dual meters.

from app.domain.entities.meter import Meter
from app.domain.ports.i_display import IDisplay
from app.domain.ports.i_leds import ILeds
from app.domain.ports.i_relay import IRelay

class HandleRemoteCommand:
    """Handle remote MQTT commands for one or two meter channels."""

    def __init__(self, meter_c0: Meter, relay_c0: IRelay, repo_c0,
                display: IDisplay, leds: ILeds, mqtt_client,
                meter_c1=None, relay_c1=None, repo_c1=None):
        self.meter_c0  = meter_c0
        self.relay_c0  = relay_c0
        self.repo_c0   = repo_c0
        self.display   = display
        self.leds      = leds
        self.mqtt      = mqtt_client
        self.meter_c1  = meter_c1
        self.relay_c1  = relay_c1
        self.repo_c1   = repo_c1

    def execute(self, serial_or_cmd: str, payload: dict) -> None:
        """
        serial_or_cmd is either the meter serial (e.g. 'CRD-2026-00001') or legacy cmd_type ('credit').
        """
        print(f"[RemoteCmd] Received command for '{serial_or_cmd}': {payload}")

        command = payload.get("command")
        # Legacy fallback if payload format is just {"kwh": ...} and serial_or_cmd is "credit"
        if not command and serial_or_cmd == "credit":
            command = "APPLY_CREDITS"

        if command == "APPLY_CREDITS":
            self._handle_apply_credits(serial_or_cmd, payload)
        else:
            print(f"[RemoteCmd] Unrecognized command '{command}' in payload: {payload}")

    def _handle_apply_credits(self, serial: str, payload: dict) -> None:
        kwh = float(payload.get("kwh", 0.0))
        command_id = str(payload.get("command_id", "desconhecido"))

        # Resolve which meter / relay / repo corresponds to this serial
        meter, relay, repo, ch_label = self._resolve_meter(serial)

        if not meter or kwh <= 0:
            print(f"[RemoteCmd] Cannot apply {kwh} kWh to serial '{serial}'")
            if self.mqtt:
                self.mqtt.publish_ack(serial, command_id, status="ERROR", applied_kwh=0.0)
            return

        try:
            # 1. Apply credit to domain entity
            meter.credit(kwh)

            # 2. Save to flash memory immediately (financial credit entered the system)
            if repo:
                repo.save(meter.balance_kwh, force=True)

            # 3. Update physical relay immediately
            if relay:
                relay.update(meter)

            # 4. Update status LEDs and LCD feedback
            if self.leds:
                self.leds.update(meter)

            if self.display:
                self.display.show_message(f"RECARGA {ch_label}", f"+{kwh:.1f} kWh")

            # 5. Send ACK to backend (mandatory so backend does not refund M-Pesa)
            if self.mqtt:
                self.mqtt.publish_ack(serial, command_id, status="ACK", applied_kwh=kwh)

            print(f"[RemoteCmd] Successfully applied {kwh} kWh to {ch_label} ({serial}). Balance: {meter.balance_kwh} kWh")

        except Exception as e:
            print(f"[RemoteCmd] Exception while applying credits to {serial}:", e)
            if self.mqtt:
                self.mqtt.publish_ack(serial, command_id, status="ERROR", applied_kwh=0.0)

    def _resolve_meter(self, serial: str):
        """Returns (meter, relay, repo, channel_label) for the given serial."""
        s = str(serial).strip()
        c1_serial = getattr(self.meter_c1, "serial_number", "") if self.meter_c1 else ""
        c0_serial = getattr(self.meter_c0, "serial_number", "") if self.meter_c0 else ""

        if self.meter_c1 and (s == c1_serial or s.endswith("00002") or s.lower() in ("c1", "canal1", "channel1")):
            return self.meter_c1, self.relay_c1, self.repo_c1, "C1"

        # Default to Canal 0
        return self.meter_c0, self.relay_c0, self.repo_c0, "C0"

