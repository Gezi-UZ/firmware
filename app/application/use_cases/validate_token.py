# app/application/use_cases/validate_token.py
# Single Responsibility: submit token → apply result to Meter and outputs.

import time


class ValidateToken:
    """
    Use-case: send the 20-digit token to the backend and apply the result.

    Architecture invariant:
      The firmware is a pure client — it submits the token and applies
      whatever the backend decides. Idempotency, hashing and uniqueness
      are exclusively backend concerns (FastAPI + Supabase).

    Dependencies (injected — DIP):
      validator   : ITokenValidator
      meter_c0    : Meter
      relay_c0    : IRelay
      repo_c0     : IStateRepository
      display     : IDisplay
      leds        : ILeds
      meter_c1    : Meter (optional)
      relay_c1    : IRelay (optional)
      repo_c1     : IStateRepository (optional)
      mqtt_client : MqttClient (optional)
    """

    def __init__(
        self,
        validator,
        meter_c0,
        relay_c0,
        repo_c0,
        display,
        leds,
        meter_c1=None,
        relay_c1=None,
        repo_c1=None,
        mqtt_client=None,
    ):
        self._validator = validator
        self._meter_c0  = meter_c0
        self._relay_c0  = relay_c0
        self._repo_c0   = repo_c0
        self._display   = display
        self._leds      = leds
        self._meter_c1  = meter_c1
        self._relay_c1  = relay_c1
        self._repo_c1   = repo_c1
        self._mqtt      = mqtt_client

    def execute(self, token: str, channel: int = 0) -> bool:
        """
        Blocking: performs one HTTP round-trip to the backend.
        Called by HandleKeypadInput after a full 20-digit buffer and channel selection.
        """
        if channel == 1 and self._meter_c1:
            meter = self._meter_c1
            relay = self._relay_c1
            repo  = self._repo_c1
            label = "C1"
        else:
            meter = self._meter_c0
            relay = self._relay_c0
            repo  = self._repo_c0
            label = "C0"

        self._display.show_message(f"A VALIDAR {label}...", "POR FAVOR AGUARDE")
        result = self._validator.validate(
            token=token,
            meter_serial=getattr(meter, "serial_number", ""),
            channel=channel,
        )

        if result.success:
            meter.credit(result.kwh)

            # Save to flash immediately! (money just entered the system)
            if repo:
                repo.save(meter.balance_kwh, force=True)

            self._display.show_message(
                f"RECARGA {label} OK!",
                "+{:.1f} kWh".format(result.kwh),
            )
            time.sleep_ms(2000)

            # Sync hardware outputs immediately so the user sees the
            # state change before the next regular loop cycle.
            if self._leds:
                self._leds.update(meter)
            if relay:
                relay.update(meter)

            # Publish updated telemetry to MQTT immediately
            if self._mqtt and self._mqtt.is_connected and getattr(meter, "serial_number", ""):
                self._mqtt.publish_telemetry(
                    serial=meter.serial_number,
                    kwh_saldo=meter.balance_kwh,
                    relay_state=relay.is_active if relay else True,
                )
            return True
        else:
            self._display.show_error(result.error)
            return False
