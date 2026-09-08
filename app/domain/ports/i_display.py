# app/domain/ports/i_display.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class IDisplay:
    """
    Abstract port for all display output.

    Concrete implementations live in app/adapters/ and depend on hardware.
    Use-cases and domain objects depend only on this interface — never on
    specific LCD hardware.
    """

    def show_state(self, meter, meter_c1=None) -> None:
        """
        Render the normal operating screen.
        Shows the supply state and balance for meter (and optionally meter_c1).
        """
        raise NotImplementedError



    def show_token_buffer(self, buffer: list) -> None:
        """
        Render the token entry screen.
        buffer: list of digit characters (0–20 elements).
        Digits are displayed grouped by 4 (e.g. '1234 5678 90')
        across two LCD rows (first 10 digits on row 1, last 10 on row 2).
        Empty positions shown as underscores.
        """
        raise NotImplementedError

    def show_message(self, line1: str, line2: str = "") -> None:
        """
        Show a transient two-line message (e.g. 'A VALIDAR...').
        Blocks briefly so the user can read the message.
        """
        raise NotImplementedError

    def show_error(self, error_code: str) -> None:
        """
        Map a backend error code to a localised message and display it.
        Blocks briefly so the user can read the error.
        """
        raise NotImplementedError
