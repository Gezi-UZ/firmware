# Concrete implementation of IMeterRepository using the ESP32 internal flash memory.

import time

try:
    # pyrefly: ignore [missing-import]
    import ujson
except ImportError:
    import json as ujson


class FlashMeterRepository:
    """
    Saves and loads the meter balance from a local JSON file (e.g. 'meter_state_c0.json').
    Implements wear-leveling with dual criteria:
      1. Delta threshold: writes immediately if consumption change >= 'save_threshold_kwh' (e.g. 0.05 kWh).
      2. Periodic interval: writes every 'save_interval_ms' (e.g. 30s) IF active consumption occurred.
      3. Force save: writes immediately on recharges, shutdown, or zero-credit cutoff.
    """

    def __init__(
        self,
        filename: str = "meter_state.json",
        save_threshold_kwh: float = 0.05,
        save_interval_ms: int = 30000,
    ):
        self._filename = filename
        self._threshold = save_threshold_kwh
        self._save_interval_ms = save_interval_ms
        self._last_saved_kwh = 0.0
        self._last_save_time_ms = time.ticks_ms()

    def load(self) -> float:
        try:
            with open(self._filename, "r") as f:
                data = ujson.load(f)
                loaded_kwh = float(data.get("kwh", 0.0))
                self._last_saved_kwh = loaded_kwh
                self._last_save_time_ms = time.ticks_ms()
                print(f"[FlashRepo:{self._filename}] Loaded balance: {loaded_kwh:.3f} kWh")
                return loaded_kwh
        except Exception:
            # File doesn't exist or is corrupted (first boot)
            print(f"[FlashRepo:{self._filename}] No valid state found. Starting at 0.0 kWh.")
            self._last_saved_kwh = 0.0
            self._last_save_time_ms = time.ticks_ms()
            return 0.0

    def save(self, current_kwh: float, force: bool = False) -> None:
        """
        Saves balance to flash if:
          - force is True (e.g. recharge applied or meter depleted to 0)
          - change >= save_threshold_kwh (e.g. 0.05 kWh)
          - save_interval_ms elapsed (e.g. 30s) AND there is pending unpersisted consumption
        """
        now = time.ticks_ms()
        diff = abs(current_kwh - self._last_saved_kwh)

        # 1. Immediate forced write
        if force:
            self._write_to_flash(current_kwh)
            self._last_save_time_ms = now
            return

        # If balance hasn't changed at all, protect flash lifespan
        if diff < 0.0005:
            return

        # 2. kWh delta threshold reached
        if diff >= self._threshold:
            self._write_to_flash(current_kwh)
            self._last_save_time_ms = now
            return

        # 3. Time interval elapsed with unpersisted consumption
        if time.ticks_diff(now, self._last_save_time_ms) >= self._save_interval_ms:
            self._write_to_flash(current_kwh)
            self._last_save_time_ms = now

    def save_if_changed(self, current_kwh: float) -> bool:
        """
        Saves immediately if the current balance differs from the last saved state.
        Useful when synchronizing with cloud telemetry or on system shutdown.
        """
        diff = abs(current_kwh - self._last_saved_kwh)
        if diff >= 0.0005:
            self._write_to_flash(current_kwh)
            self._last_save_time_ms = time.ticks_ms()
            return True
        return False

    def _write_to_flash(self, kwh: float) -> None:
        try:
            with open(self._filename, "w") as f:
                ujson.dump({"kwh": round(kwh, 3)}, f)
            self._last_saved_kwh = round(kwh, 3)
            print(f"[FlashRepo:{self._filename}] Saved to flash: {self._last_saved_kwh:.3f} kWh")
        except Exception as e:
            print(f"[FlashRepo:{self._filename}] ERROR saving state: {e}")


