# app/application/use_cases/validate_token.py
# Single Responsibility: submit token → apply result to Meter and outputs.


class ValidateToken:
    """
    Use-case: send the 20-digit token to the backend and apply the result.

    Architecture invariant:
      The firmware is a pure client — it submits the token and applies
      whatever the backend decides. Idempotency, hashing and uniqueness
      are exclusively backend concerns (FastAPI + Supabase).

    Success flow:
      display "A VALIDAR..." → POST /token/validate
        → 200 OK { kwh: X }
        → meter.credit(X)
        → display "RECARGA OK! +X kWh"
        → outputs sync on next loop cycle

    Error flow:
      → display localised error message (e.g. "JA UTILIZADO")
      → meter unchanged

    Dependencies (injected — DIP):
      validator : ITokenValidator
      meter     : Meter
      display   : IDisplay
      leds      : ILeds
      relay     : IRelay
    """

    def __init__(self, validator, meter, display, leds, relay):
        self._validator = validator
        self._meter     = meter
        self._display   = display
        self._leds      = leds
        self._relay     = relay

    def execute(self, token: str) -> None:
        """
        Blocking: performs one HTTP round-trip to the backend.
        Called by HandleKeypadInput after a full 20-digit buffer is confirmed.
        """
        self._display.show_message("A VALIDAR...", "POR FAVOR AGUARDE")
        result = self._validator.validate(token)

        if result.success:
            self._meter.credit(result.kwh)
            self._display.show_message(
                "RECARGA OK!",
                "+{:.1f} kWh".format(result.kwh),
            )
            # Sync hardware outputs immediately so the user sees the
            # state change before the next regular loop cycle.
            self._leds.update(self._meter)
            self._relay.update(self._meter)
        else:
            self._display.show_error(result.error)
