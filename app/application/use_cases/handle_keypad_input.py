# app/application/use_cases/handle_keypad_input.py
# Single Responsibility: manage the 20-digit token buffer and dispatch submission.


class HandleKeypadInput:
    """
    Use-case: accumulate keypad presses into a 20-digit token buffer
    and submit for backend validation when the user confirms.

    Key behaviour
    -------------
    0–9  Append digit to buffer (up to MAX_DIGITS = 20).
         Display updates in real-time, grouped by 4 digits per group.
         Example after 14 digits:
           Line 1 →  1234 5678 90____
           Line 2 →  1234 ________
    B    Backspace — remove the last digit from the buffer.
    C    Cancel — clear the entire buffer.
    A    Confirm — submit token only when buffer is exactly MAX_DIGITS.
         The buffer is cleared before delegating to ValidateToken.

    Dependencies (injected — DIP):
      keypad          : IKeypad
      display         : IDisplay
      validate_token  : ValidateToken  (use-case, not the adapter)
    """

    MAX_DIGITS = 20

    def __init__(self, keypad, display, validate_token_uc):
        self._keypad   = keypad
        self._display  = display
        self._validate = validate_token_uc
        self._buffer   = []  # list of digit characters, max MAX_DIGITS

    def execute(self) -> None:
        """Non-blocking. Called every main-loop iteration."""
        key = self._keypad.scan()
        if key is None:
            return

        if key.isdigit():
            self._on_digit(key)
        elif key == "B":
            self._on_backspace()
        elif key == "C":
            self._on_cancel()
        elif key == "A":
            self._on_confirm()
        # '*', '#', 'D' → ignored (reserved for future use)

    # ── key handlers ─────────────────────────────────────────────────────────

    def _on_digit(self, digit: str) -> None:
        if len(self._buffer) < self.MAX_DIGITS:
            self._buffer.append(digit)
            self._display.show_token_buffer(self._buffer)

    def _on_backspace(self) -> None:
        if self._buffer:
            self._buffer.pop()
            self._display.show_token_buffer(self._buffer)

    def _on_cancel(self) -> None:
        self._buffer.clear()
        self._display.show_token_buffer(self._buffer)

    def _on_confirm(self) -> None:
        if len(self._buffer) < self.MAX_DIGITS:
            # Token incomplete — give visual feedback but do not submit
            self._display.show_message(
                "CODIGO INCOMPLETO",
                "{}/20 DIGITOS".format(len(self._buffer)),
            )
            return
        token = "".join(self._buffer)
        self._buffer.clear()
        self._validate.execute(token)
