# app/application/use_cases/update_outputs.py
# Single Responsibility: keep all output peripherals in sync with the Meter(s).


class UpdateOutputs:
    """
    Use-case: synchronise display, LEDs and relays with the Meter states.
    Supports dual channels (meter_c0 and meter_c1).
    """

    def __init__(self, display, leds, relay_c0, relay_c1=None):
        self._display  = display
        self._leds     = leds
        self._relay_c0 = relay_c0
        self._relay_c1 = relay_c1

    def execute(self, meter_c0, meter_c1=None) -> None:
        """
        Render the normal operating state across all output peripherals.
        Do NOT call this during token entry or validation — the display
        is owned by HandleKeypadInput / ValidateToken at those moments.
        """
        self._display.show_state(meter_c0, meter_c1)

        # Update relays
        self._relay_c0.update(meter_c0)
        if self._relay_c1 and meter_c1:
            self._relay_c1.update(meter_c1)

        # Update LEDs (reflect overall system state)
        if meter_c1 is not None:
            if meter_c0.state == "WARNING" or meter_c1.state == "WARNING":
                self._leds.update(meter_c0 if meter_c0.state == "WARNING" else meter_c1)
            elif meter_c0.supply_active or meter_c1.supply_active:
                self._leds.update(meter_c0 if meter_c0.supply_active else meter_c1)
            else:
                self._leds.update(meter_c0)
        else:
            self._leds.update(meter_c0)


