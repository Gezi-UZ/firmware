# app/adapters/http_token_validator.py
# Concrete ITokenValidator — HTTP POST to the Gezi FastAPI backend.

try:
    # pyrefly: ignore [missing-import]
    import ujson
except ImportError:
    import json as ujson

from app.domain.ports.i_token_validator import ITokenValidator
from app.domain.value_objects.token_result import TokenResult


class HttpTokenValidator(ITokenValidator):
    """
    Validates a 20-digit recharge token by calling the Gezi backend API.

    POST {base_url}/token/validate
    Body: { "token": "<20-digit string>", "device_id": "<DEVICE_ID>" }

    Success response (HTTP 200):
      { "kwh": 50.0, "token_id": "...", ... }

    Error response (HTTP 4xx/5xx — FastAPI format):
      { "detail": "TOKEN_ALREADY_USED" }
      or validation errors:
      { "detail": [{ "msg": "...", "type": "..." }] }

    Architecture invariant:
      All business rules (hashing, idempotency, Supabase persistence)
      are enforced exclusively by the backend. This adapter is a
      pure HTTP client — it sends and receives, nothing more.
    """

    def __init__(self, base_url: str, device_id: str):
        self._url       = base_url.rstrip("/") + "/token/validate"
        self._device_id = device_id

    def validate(self, token: str) -> TokenResult:
        """
        Blocking HTTP round-trip.
        Returns TokenResult(success=False, error="SEM_LIGACAO") on any
        network/timeout exception so the caller always receives a clean VO.
        """
        try:
            # pyrefly: ignore [missing-import]
            import urequests  # MicroPython built-in

            payload = ujson.dumps({
                "token":     token,
                "device_id": self._device_id,
            })
            response = urequests.post(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            status = response.status_code
            body   = response.json()
            response.close()

            if status == 200:
                kwh = float(body.get("kwh", 0.0))
                return TokenResult(success=True, kwh=kwh)

            # Extract error code from FastAPI response
            detail = body.get("detail", "ERRO_DESCONHECIDO")
            if isinstance(detail, list):
                # FastAPI validation error format: list of error dicts
                error = detail[0].get("msg", "ERRO_VALIDACAO") if detail else "ERRO_VALIDACAO"
            else:
                error = str(detail)

            return TokenResult(success=False, error=error)

        except Exception:
            return TokenResult(success=False, error="SEM_LIGACAO")
