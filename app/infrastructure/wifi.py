import network
import time


class WifiService:
    """
    Manages the ESP32 WiFi station connection.
    Required before any HTTP token validation or MQTT publishing.
    """

    CONNECT_TIMEOUT_S = 15
    RETRY_INTERVAL_MS = 500

    def __init__(self, ssid: str, password: str):
        self._ssid     = ssid
        self._password = password
        self._wlan     = network.WLAN(network.STA_IF)

    def connect(self) -> bool:
        """
        Connect to the configured WiFi network.
        Blocks until connected or CONNECT_TIMEOUT_S is reached.
        Returns True on success, False on timeout.
        """
        self._wlan.active(True)

        if self._wlan.isconnected():
            print("[WiFi] Already connected:", self._wlan.ifconfig())
            return True

        print("[WiFi] Connecting to '{}'...".format(self._ssid))
        self._wlan.connect(self._ssid, self._password)

        deadline = time.time() + self.CONNECT_TIMEOUT_S
        while not self._wlan.isconnected():
            if time.time() > deadline:
                print("[WiFi] Connection timed out after {}s".format(
                    self.CONNECT_TIMEOUT_S))
                return False
            time.sleep_ms(self.RETRY_INTERVAL_MS)

        ip, mask, gw, dns = self._wlan.ifconfig()
        print("[WiFi] Connected — IP: {}  GW: {}".format(ip, gw))
        return True

    def is_connected(self) -> bool:
        """Return True if the station interface is currently connected."""
        return self._wlan.isconnected()

    def get_mac_address(self) -> str:
        """
        Returns the formatted MAC address string (e.g. 'ec:60:04:xx:yy:zz').
        Used for Auto-Discovery (Hello) and unique client identification.
        """
        try:
            self._wlan.active(True)
            # pyrefly: ignore [missing-import]
            import ubinascii
            return ubinascii.hexlify(self._wlan.config("mac"), ":").decode()
        except Exception:
            try:
                import binascii
                # Fallback for standard Python / testing
                mac_bytes = self._wlan.config("mac")
                return binascii.hexlify(mac_bytes, ":").decode()
            except Exception:
                return "00:00:00:00:00:00"

    def get_ip(self) -> str:
        """Returns the assigned IP address string."""
        try:
            return self._wlan.ifconfig()[0]
        except Exception:
            return "0.0.0.0"

    def disconnect(self) -> None:
        """Disconnect and deactivate the WiFi interface."""
        self._wlan.disconnect()
        self._wlan.active(False)
        print("[WiFi] Disconnected")

