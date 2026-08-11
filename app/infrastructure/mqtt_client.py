# app/infrastructure/mqtt_client.py
# Real MQTT client implementation using umqtt.simple

try:
    # pyrefly: ignore [missing-import]
    import ujson
except ImportError:
    import json as ujson
import time

class MqttClient:
    """
    Publishes Meter telemetry and domain events to the Mosquitto/HiveMQ broker.
    Also subscribes to command topics to receive remote actions (e.g. remote recharge).
    Uses umqtt.simple (bundled in MicroPython firmware).
    """

    def __init__(self, broker_host: str, device_id: str,
                 port: int = 1883,
                 username: str = "", password: str = "",
                 use_tls: bool = False):
        
        # We import here so tests/linters without umqtt don't crash instantly
        try:
            # pyrefly: ignore [missing-import]
            from umqtt.simple import MQTTClient as _UMqtt
        except ImportError:
            print("[MQTT] WARNING: umqtt.simple not found. Running in mock mode.")
            _UMqtt = None

        self._device_id = device_id
        self._topic_tel = f"gezi/{device_id}/telemetry".encode()
        self._topic_evt = f"gezi/{device_id}/events".encode()
        self._topic_cmd = f"gezi/{device_id}/cmd/#".encode()

        if _UMqtt:
            self._client = _UMqtt(
                client_id=device_id,
                server=broker_host,
                port=port,
                user=username or None,
                password=password or None,
                keepalive=60,
                ssl=use_tls,
                ssl_params={"server_side": False} if use_tls else {}
            )
        else:
            self._client = None
            
        self._on_cmd_callback = None

    def connect(self) -> bool:
        if not self._client:
            return False
            
        try:
            self._client.set_callback(self._on_message)
            self._client.connect()
            self._client.subscribe(self._topic_cmd)
            print(f"[MQTT] Connected and subscribed to {self._topic_cmd.decode()}")
            return True
        except Exception as e:
            print("[MQTT] Connect failed:", e)
            return False

    def publish_telemetry(self, meter, reading=None) -> None:
        """Publishes real-time state to the telemetry topic."""
        if not self._client:
            return
            
        payload = ujson.dumps({
            "device_id":     self._device_id,
            "ts":            time.time(),
            "kwh":           meter.balance_kwh,
            "state":         meter.state,
            "supply_active": meter.supply_active,
            "power_w":       reading.power_w   if reading else 0.0,
            "voltage_v":     reading.voltage_v if reading else 0.0,
            "current_a":     reading.current_a if reading else 0.0,
            "sim":           True, # Adjust based on PZEM_SIMULATE if needed
        })
        try:
            self._client.publish(self._topic_tel, payload, qos=1)
        except Exception as e:
            print("[MQTT] Publish telemetry error:", e)

    def publish_event(self, event_type: str, kwh_credited: float = 0.0, meter=None) -> None:
        """Publishes significant events (like recharges) to the events topic."""
        if not self._client:
            return
            
        payload = ujson.dumps({
            "device_id":   self._device_id,
            "ts":          time.time(),
            "type":        event_type,
            "kwh_credited": kwh_credited,
            "kwh_balance":  meter.balance_kwh if meter else 0.0,
        })
        try:
            self._client.publish(self._topic_evt, payload, qos=1)
        except Exception as e:
            print("[MQTT] Publish event error:", e)

    def check_messages(self) -> None:
        """
        Call every loop iteration to process incoming MQTT messages.
        This is non-blocking (in umqtt.simple check_msg doesn't block).
        """
        if not self._client:
            return
            
        try:
            self._client.check_msg()
        except Exception as e:
            # Handle potential connection drops here in production
            pass

    def set_command_callback(self, callback) -> None:
        """
        Register a function to be called when a message arrives on the cmd/# topic.
        Signature: callback(cmd_type: str, payload: dict)
        """
        self._on_cmd_callback = callback

    def _on_message(self, topic, msg) -> None:
        """Internal callback fired by umqtt when a message arrives."""
        try:
            payload = ujson.loads(msg)
            topic_str = topic.decode()
            
            # e.g., topic: "gezi/GEZI-ESP32-001/cmd/credit" -> cmd_type: "credit"
            cmd_type = topic_str.split("/")[-1]
            
            if self._on_cmd_callback:
                self._on_cmd_callback(cmd_type, payload)
        except Exception as e:
            print(f"[MQTT] Message parse error on topic {topic}:", e)

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.disconnect()
                print("[MQTT] Disconnected cleanly.")
            except Exception:
                pass
