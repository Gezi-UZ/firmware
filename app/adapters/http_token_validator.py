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
    Body: { "token": "<20-digit string>", "device_id": "<DEVICE_ID>", "meter_serial": "<SERIAL>", "channel": 0 }

    Success response (HTTP 200/201):
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

    def validate(self, token: str, meter_serial: str = "", channel: int = 0) -> TokenResult:
        """
        Blocking HTTP round-trip.
        Returns TokenResult(success=False, error="SEM_LIGACAO") on any
        network/timeout exception so the caller always receives a clean VO.
        """
        try:
            # pyrefly: ignore [missing-import]
            import urequests  # MicroPython built-in

            payload = ujson.dumps({
                "token":        token,
                "device_id":    self._device_id,
                "meter_serial": meter_serial,
                "channel":      channel,
            })
            print(f"[HttpTokenValidator] Sending token validation: {payload}")
            response = urequests.post(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            status = response.status_code
            body   = response.json()
            response.close()

            print(f"[HttpTokenValidator] Response ({status}): {body}")

            if status in (200, 201):
                data_dict = body.get("data") if isinstance(body.get("data"), dict) else body
                kwh = float(data_dict.get("kwh") or data_dict.get("credit_kwh") or data_dict.get("applied_kwh") or 0.0)
                return TokenResult(success=True, kwh=kwh)

            # Extract error code from FastAPI response
            detail = body.get("detail", "ERRO_DESCONHECIDO")
            if isinstance(detail, list):
                # FastAPI validation error format: list of error dicts
                error = detail[0].get("msg", "ERRO_VALIDACAO") if detail else "ERRO_VALIDACAO"
            elif isinstance(detail, dict):
                error = detail.get("message", "ERRO_VALIDACAO")
            else:
                error = str(detail)

            return TokenResult(success=False, error=error)

        except Exception as e:
            print("[HttpTokenValidator] Network error:", e)
            return TokenResult(success=False, error="SEM_LIGACAO")

