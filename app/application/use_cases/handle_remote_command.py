# Use-case: Handles incoming MQTT commands from the backend.

from app.domain.entities.meter import Meter
from app.domain.ports.i_display import IDisplay
from app.domain.ports.i_leds import ILeds
from app.domain.ports.i_relay import IRelay

class HandleRemoteCommand:
    """
    Executes actions based on remote commands received via MQTT.
    Example: Mobile App -> FastAPI -> HiveMQ -> ESP32 (this use case).
    """

    def __init__(self, meter: Meter, display: IDisplay, leds: ILeds, relay: IRelay, mqtt_client):
        self.meter   = meter
        self.display = display
        self.leds    = leds
        self.relay   = relay
        self.mqtt    = mqtt_client

    def execute(self, cmd_type: str, payload: dict) -> None:
        """
        Process a remote command.
        cmd_type is the last part of the MQTT topic (e.g., 'credit').
        """
        print(f"[RemoteCmd] Received '{cmd_type}' with payload: {payload}")

        if cmd_type == "credit":
            kwh = float(payload.get("kwh", 0.0))
            if kwh > 0:
                # 1. Apply credit to domain entity
                self.meter.credit(kwh)
                
                # 2. Provide local UI feedback
                self.display.show_message("RECARGA REMOTA", f"+{kwh:.1f} kWh")
                
                # 3. Update hardware outputs (Relay, LEDs)
                self.leds.update(self.meter)
                self.relay.update(self.meter)
                
                # 4. Acknowledge back to the cloud
                self.mqtt.publish_event(
                    event_type="RECHARGE_APPLIED",
                    kwh_credited=kwh,
                    meter=self.meter
                )
                print(f"[RemoteCmd] Successfully applied {kwh} kWh.")
        
        elif cmd_type == "reset":
            # Future expansion (e.g., reset meter state)
            pass
        else:
            print(f"[RemoteCmd] Unknown command type: {cmd_type}")
