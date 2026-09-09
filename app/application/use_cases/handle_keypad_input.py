# app/application/use_cases/handle_keypad_input.py
# Single Responsibility: manage the 20-digit token buffer, channel selection, and dispatch submission.

import time

STATE_IDLE = 0
STATE_INPUT = 1
STATE_SELECT_CHANNEL = 2


class HandleKeypadInput:
    """
    Use-case: accumulate keypad presses into a 20-digit token buffer,
    prompt for channel selection (C0 or C1), and submit for backend validation.

    Key behaviour
    -------------
    Em modo normal (STATE_IDLE):
      0–9  Muda para tela de input e insere o primeiro dígito.

    Em modo de digitação (STATE_INPUT):
      0–9  Adiciona dígito ao buffer (até MAX_DIGITS = 20).
           O LCD é atualizado imediatamente (primeiros 10 dígitos na linha 1,
           últimos 10 dígitos na linha 2, agrupados de 4 em 4).
      B    Backspace — remove o último dígito. Se buffer esvaziar, volta ao IDLE.
      C    Cancel — limpa o buffer e volta imediatamente à tela normal.
      A    Confirm — se tiver 20 dígitos, abre o prompt para escolher o canal.
           Se tiver menos de 20, avisa 'CODIGO INCOMPLETO' e re-exibe os dígitos.

    Em modo de escolha de canal (STATE_SELECT_CHANNEL):
      LCD mostra:
        Linha 1: 'RECARREGAR CANAL'
        Linha 2: '1: C0    2: C1'
      1 / 0 / A: Seleciona Canal 0 (C0) e submete validação.
      2 / B:     Seleciona Canal 1 (C1) e submete validação.
      C:         Cancela e volta ao modo normal.

    Inactivity:
      Após 30 segundos sem premir teclas durante a digitação ou prompt,
      cancela automaticamente e regressa ao ecrã normal.
    """

    MAX_DIGITS = 20
    INACTIVITY_TIMEOUT_MS = 30000  # 30 segundos

    def __init__(self, keypad, display, validate_token_uc):
        self._keypad   = keypad
        self._display  = display
        self._validate = validate_token_uc
        self._buffer   = []
        self._state    = STATE_IDLE
        self._last_activity_ms = 0

    @property
    def is_active(self) -> bool:
        """True when user is actively interacting with the keypad (typing or prompt)."""
        return self._state != STATE_IDLE

    def execute(self) -> None:
        """Non-blocking. Called every main-loop iteration."""
        now = time.ticks_ms()

        # Handle inactivity timeout
        if self._state != STATE_IDLE:
            if time.ticks_diff(now, self._last_activity_ms) > self.INACTIVITY_TIMEOUT_MS:
                print("[Keypad] Inactivity timeout — returning to idle.")
                self._cancel()
                return

        key = self._keypad.scan()
        if key is None:
            return

        self._last_activity_ms = now

        if self._state == STATE_SELECT_CHANNEL:
            self._handle_channel_selection(key)
        else:
            self._handle_token_input(key)

    # ── Input Handlers ────────────────────────────────────────────────────────

    def _handle_token_input(self, key: str) -> None:
        if key.isdigit():
            if self._state == STATE_IDLE:
                self._state = STATE_INPUT
                self._buffer.clear()

            if len(self._buffer) < self.MAX_DIGITS:
                self._buffer.append(key)
                self._display.show_token_buffer(self._buffer)

        elif key == "B":
            if self._state == STATE_INPUT and self._buffer:
                self._buffer.pop()
                if self._buffer:
                    self._display.show_token_buffer(self._buffer)
                else:
                    self._cancel()

        elif key == "C":
            self._cancel()

        elif key == "A":
            if self._state == STATE_INPUT:
                if len(self._buffer) < self.MAX_DIGITS:
                    self._display.show_message(
                        "CODIGO INCOMPLETO",
                        "{}/20 DIGITOS".format(len(self._buffer)),
                    )
                    self._display.show_token_buffer(self._buffer)
                else:
                    # Exactly 20 digits: proceed to channel selection prompt
                    self._state = STATE_SELECT_CHANNEL
                    self._display.show_prompt("RECARREGAR CANAL", "1: C0    2: C1")

    def _handle_channel_selection(self, key: str) -> None:
        if key in ("1", "0", "A"):
            token = "".join(self._buffer)
            self._buffer.clear()
            self._state = STATE_IDLE
            print(f"[Keypad] Confirmed token for Canal 0: {token}")
            self._validate.execute(token=token, channel=0)

        elif key in ("2", "B"):
            token = "".join(self._buffer)
            self._buffer.clear()
            self._state = STATE_IDLE
            print(f"[Keypad] Confirmed token for Canal 1: {token}")
            self._validate.execute(token=token, channel=1)

        elif key == "C":
            self._cancel()

    def _cancel(self) -> None:
        self._buffer.clear()
        self._state = STATE_IDLE

