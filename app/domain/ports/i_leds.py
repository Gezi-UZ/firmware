# app/domain/ports/i_leds.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class ILeds:
    """
    Abstract port for LED status indicators.

    State → LED behaviour mapping (defined by business rules in README):
      CREDIT    → green ON,  red OFF
      WARNING   → green ON,  red BLINK 1 Hz
      NO_CREDIT → green OFF, red ON (solid)
    """

    def update(self, meter) -> None:
        """
        Synchronise LED states with the current meter state.
        Hardware Timer blinking must not block the main loop.
        """
        raise NotImplementedError
