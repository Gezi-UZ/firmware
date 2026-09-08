# Concrete implementation of IMeterRepository using the ESP32 internal flash memory.

try:
    # pyrefly: ignore [missing-import]
    import ujson
except ImportError:
    import json as ujson

class FlashMeterRepository:
    """
    Saves and loads the meter balance from a local JSON file ('meter_state.json').
    Implements wear-leveling by only writing to flash if the balance changed 
    by at least 'save_threshold_kwh' (e.g., 0.1 kWh), unless forced.
    """

    def __init__(self, filename: str = "meter_state.json", save_threshold_kwh: float = 0.1):
        self._filename = filename
        self._threshold = save_threshold_kwh
        self._last_saved_kwh = 0.0

    def load(self) -> float:
        try:
            with open(self._filename, "r") as f:
                data = ujson.load(f)
                loaded_kwh = float(data.get("kwh", 0.0))
                self._last_saved_kwh = loaded_kwh
                print(f"[FlashRepo] Loaded existing balance: {loaded_kwh} kWh")
                print(f"[FlashRepo:{self._filename}] Loaded existing balance: {loaded_kwh} kWh")
                return loaded_kwh
        except Exception:
            # File doesn't exist or is corrupted (first boot)
            print("[FlashRepo] No valid state found. Starting at 0.0 kWh.")
            print(f"[FlashRepo:{self._filename}] No valid state found. Starting at 0.0 kWh.")
            self._last_saved_kwh = 0.0
            return 0.0

    def save(self, current_kwh: float, force: bool = False) -> None:
        # Check if we need to save to protect Flash lifespan
        diff = abs(current_kwh - self._last_saved_kwh)
        
        if force or diff >= self._threshold:
            self._write_to_flash(current_kwh)
            
    def _write_to_flash(self, kwh: float) -> None:
        try:
            with open(self._filename, "w") as f:
                ujson.dump({"kwh": kwh}, f)
            self._last_saved_kwh = kwh
            print(f"[FlashRepo] State saved to flash: {kwh} kWh")
            print(f"[FlashRepo:{self._filename}] State saved to flash: {kwh} kWh")
        except Exception as e:
            print(f"[FlashRepo] ERROR saving state: {e}")
            print(f"[FlashRepo:{self._filename}] ERROR saving state: {e}")

