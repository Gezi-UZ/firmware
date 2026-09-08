# app/infrastructure/mqtt_client.py
# Real MQTT client implementation using umqtt.simple, supporting dual-channel meters,
# HiveMQ TLS with SNI, auto-discovery (Hello), command ACK and continuous telemetry.

try:
    # pyrefly: ignore [missing-import]
    import ujson
except ImportError:
    import json as ujson
import time


class MqttClient:
    """
    Manages MQTT communication with HiveMQ Cloud (TLS port 8883) for dual meters.
    Responsibilities:
        - Connect with TLS and server_hostname (SNI requirement).
        - Auto-Discovery: publish hello message to gezi/v1/{mac}/hello.
        - Subscribe to command topics for both meters (Channel 0 and Channel 1).
        - Route incoming commands with meter serial extraction to use-case callbacks.
        - Publish ACK to credelec/meter/{serial}/ack.
        - Publish continuous telemetry to credelec/meter/{serial}/telemetry.
        - Handle disconnections and support non-blocking reconnection.
    """

    def __init__(
        self,
        broker_host: str,
        client_id: str,
        port: int = 8883,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        meter_serial_c0: str = "",
        meter_serial_c1: str = "",
    ):
        try:
            from umqtt.simple import MQTTClient as _UMqtt  # pyright: ignore[reportMissingImports]
        except ImportError:
            print("[MQTT] WARNING: umqtt.simple not found. Running in mock mode.")
            _UMqtt = None

        self._broker_host = broker_host
        self._port = port
        self._client_id = client_id
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._serial_c0 = meter_serial_c0
        self._serial_c1 = meter_serial_c1
        self._UMqtt = _UMqtt

        self._client = None
        self._connected = False
        self._last_reconnect_attempt = 0
        self._on_cmd_callback = None
        self._last_mac = client_id
        self._last_ip = ""

        self._init_client()

    def _init_client(self) -> None:
        if not self._UMqtt:
            self._client = None
            return

        ssl_params = {}
        if self._use_tls:
            # HiveMQ Cloud requires SNI (server_hostname) in ssl_params
            ssl_params = {"server_hostname": self._broker_host}

        self._client = self._UMqtt(
            client_id=self._client_id,
            server=self._broker_host,
            port=self._port,
            user=self._username or None,
            password=self._password or None,
            keepalive=60,
            ssl=self._use_tls,
            ssl_params=ssl_params,
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Connects to the MQTT broker and subscribes to command topics."""
        if not self._client:
            self._init_client()
            if not self._client:
                return False

        try:
            self._client.set_callback(self._on_message)
            self._client.connect()
            self._connected = True
            print(
                f"[MQTT] Connected successfully to HiveMQ ({self._broker_host}:{self._port})"
            )

            # Subscribe to command topics for both meters (QoS 1)
            if self._serial_c0:
                topic_c0 = f"credelec/meter/{self._serial_c0}/cmd"
                self._client.subscribe(topic_c0, qos=1)
                print(f"[MQTT] Subscribed to {topic_c0}")

            if self._serial_c1:
                topic_c1 = f"credelec/meter/{self._serial_c1}/cmd"
                self._client.subscribe(topic_c1, qos=1)
                print(f"[MQTT] Subscribed to {topic_c1}")

            return True
        except Exception as e:
            self._connected = False
            print("[MQTT] Connect failed:", e)
            return False

    def publish_hello(
        self, mac_address: str, ip_address: str, firmware: str = "v1.2.0-dual"
    ) -> bool:
        """
        Step 1 (Auto-Discovery): Publish MAC address and IP to gezi/v1/{mac}/hello (QoS 1).
        Informs backend to register or update the IoT edge device.
        """
        self._last_mac = mac_address
        self._last_ip = ip_address

        if not self._client or not self._connected:
            return False

        topic = f"gezi/v1/{mac_address}/hello"
        payload = ujson.dumps({"firmware": firmware, "ip": ip_address})

        try:
            self._client.publish(topic, payload, qos=1)
            print(f"[MQTT] Sent Hello to {topic}: {payload}")
            return True
        except Exception as e:
            print(f"[MQTT] Error publishing hello to {topic}:", e)
            self._connected = False
            return False

    def publish_ack(
        self,
        serial: str,
        command_id: str,
        status: str = "ACK",
        applied_kwh: float = 0.0,
    ) -> bool:
        """
        Step 4: Confirm command execution to backend (QoS 1).
        Topic: credelec/meter/{serial}/ack
        """
        if not self._client or not self._connected:
            return False

        topic = f"credelec/meter/{serial}/ack"
        payload = ujson.dumps(
            {"command_id": command_id, "status": status, "applied_kwh": applied_kwh}
        )

        try:
            self._client.publish(topic, payload, qos=1)
            print(f"[MQTT] Sent ACK to {topic}: {payload}")
            return True
        except Exception as e:
            print(f"[MQTT] Error publishing ACK to {topic}:", e)
            self._connected = False
            return False

    def publish_telemetry(
        self, serial: str, kwh_saldo: float, relay_state: bool, reading=None
    ) -> bool:
        """
        Step 5: Publish periodic telemetry to credelec/meter/{serial}/telemetry (QoS 0).
        """
        if not self._client or not self._connected:
            return False

        topic = f"credelec/meter/{serial}/telemetry"
        payload_dict = {"kwh": round(kwh_saldo, 2), "relay": bool(relay_state)}

        if reading:
            payload_dict["voltage"] = round(reading.voltage_v, 1)
            payload_dict["current"] = round(reading.current_a, 2)
            payload_dict["power_w"] = round(reading.power_w, 1)

        payload = ujson.dumps(payload_dict)

        try:
            self._client.publish(topic, payload, qos=0)
            return True
        except Exception as e:
            print(f"[MQTT] Error publishing telemetry to {topic}:", e)
            self._connected = False
            return False

    def check_messages(self) -> None:
        """
        Non-blocking check for incoming MQTT messages on subscribed topics.
        Safely catches network/socket errors without crashing the main loop.
        """
        if not self._client or not self._connected:
            return

        try:
            self._client.check_msg()
        except Exception as e:
            print("[MQTT] Connection dropped in check_msg:", e)
            self._connected = False

    def reconnect_if_needed(self, now_ms: int, interval_ms: int = 10000) -> bool:
        """
        Attempts non-blocking reconnection if connection was lost.
        """
        if self._connected:
            return True

        if time.ticks_diff(now_ms, self._last_reconnect_attempt) < interval_ms:
            return False

        self._last_reconnect_attempt = now_ms
        print("[MQTT] Attempting to reconnect to HiveMQ...")
        success = self.connect()
        if success and self._last_mac:
            self.publish_hello(self._last_mac, self._last_ip)
        return success

    def set_command_callback(self, callback) -> None:
        """
        Register callback function for incoming commands.
        Signature: callback(serial: str, payload: dict)
        """
        self._on_cmd_callback = callback

    def _on_message(self, topic, msg) -> None:
        """Internal callback fired by umqtt when a message arrives."""
        try:
            topic_str = topic.decode() if isinstance(topic, bytes) else str(topic)
            msg_str = msg.decode() if isinstance(msg, bytes) else str(msg)
            payload = ujson.loads(msg_str)

            print(f"[MQTT] Received on {topic_str}: {payload}")

            # Extract meter serial number from topic 'credelec/meter/{serial}/cmd'
            parts = topic_str.split("/")
            if len(parts) >= 3 and parts[0] == "credelec" and parts[1] == "meter":
                serial = parts[2]
            else:
                serial = self._serial_c0  # fallback

            if self._on_cmd_callback:
                self._on_cmd_callback(serial, payload)
        except Exception as e:
            print(f"[MQTT] Error processing message on {topic}:", e)

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.disconnect()
                self._connected = False
                print("[MQTT] Disconnected cleanly.")
            except Exception:
                pass
