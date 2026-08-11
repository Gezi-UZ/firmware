# app/domain/ports/i_token_validator.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class ITokenValidator:
    """
    Abstract port for recharge token validation.

    Architecture invariant:
      The firmware NEVER validates tokens locally.
      This interface is the boundary between the firmware and the
      Gezi backend (FastAPI + Supabase). All business logic regarding
      token hashing, idempotency and uniqueness lives exclusively in
      the backend.
    """

    def validate(self, token: str):
        """
        Submit a 20-digit token to the validation service.

        Parameters
        ----------
        token : str
            The 20-digit numeric string entered by the user.

        Returns
        -------
        TokenResult
            Value object with success flag, kWh credit, and optional error code.

        Notes
        -----
        This call is blocking (performs an HTTP round-trip).
        The concrete adapter is responsible for timeout and error handling.
        """
        raise NotImplementedError
