# app/domain/ports/i_keypad.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class IKeypad:
    """
    Abstract port for keypad input.

    scan() must be non-blocking so it can be called every 100 ms in the
    main loop without stalling other operations.
    """

    def scan(self):
        """
        Return the character of the currently pressed key, or None.
        Must be non-blocking (returns immediately).
        Debounce is the responsibility of the concrete implementation.
        """
        raise NotImplementedError
