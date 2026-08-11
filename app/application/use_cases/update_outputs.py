# app/application/use_cases/update_outputs.py
# Single Responsibility: keep all output peripherals in sync with the Meter.


class UpdateOutputs:
    """
    Use-case: synchronise display, LEDs and relay with the current Meter state.

    Called on every main-loop iteration to ensure the UI always reflects the
    latest balance and supply state, even as the balance changes due to
    background consumption.

    Dependencies (injected — DIP):
      display : IDisplay
      leds    : ILeds
      relay   : IRelay
    """

    def __init__(self, display, leds, relay):
        self._display = display
        self._leds    = leds
        self._relay   = relay

    def execute(self, meter) -> None:
        """
        Render the normal operating state across all output peripherals.
        Do NOT call this during token entry or validation — the display
        is owned by HandleKeypadInput / ValidateToken at those moments.
        """
        self._display.show_state(meter)
        self._leds.update(meter)
        self._relay.update(meter)
