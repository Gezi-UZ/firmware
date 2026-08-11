# app/domain/value_objects/token_result.py
# Immutable result returned by ITokenValidator.validate().


class TokenResult:
    """
    Value object representing the outcome of a token validation request.

    Fields
    ------
    success : True when the backend accepted the token.
    kwh     : Credit to apply (only meaningful when success=True).
    error   : Backend error code string (when success=False).
              Examples: "TOKEN_ALREADY_USED", "TOKEN_NOT_FOUND",
                        "TOKEN_EXPIRED", "SEM_LIGACAO".
    """

    __slots__ = ("success", "kwh", "error")

    def __init__(self, success: bool, kwh: float = 0.0, error: str = ""):
        self.success = success
        self.kwh     = float(kwh)
        self.error   = error

    def __repr__(self) -> str:
        if self.success:
            return "TokenResult(OK, kwh={})".format(self.kwh)
        return "TokenResult(FAIL, error={!r})".format(self.error)
