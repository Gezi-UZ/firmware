# app/domain/entities/meter.py
# Central domain entity — pure Python, zero hardware imports.


# ── State constants ───────────────────────────────────────────────────────────
NO_CREDIT = "NO_CREDIT"  # balance == 0.0 kWh  → relay OFF, red LED solid
WARNING   = "WARNING"    # 0.0 < balance < 5.0 → relay ON,  red LED blinks
CREDIT    = "CREDIT"     # balance >= 5.0      → relay ON,  green LED solid

_WARNING_KWH = 5.0


class Meter:
    """
    Aggregate root for the energy metering domain.

    Responsibilities:
      - Track the kWh balance.
      - Derive the supply state (CREDIT / WARNING / NO_CREDIT).
      - Apply validated backend credits.
      - Deduct measured consumption (applied by the energy monitor).

    Invariants:
      - balance is never negative.
      - Only the backend can grant credit (token validated upstream).
    """

    def __init__(self, initial_kwh: float = 0.0):
        self._kwh = float(initial_kwh)

    # ── Commands ──────────────────────────────────────────────────────────────

    def credit(self, kwh: float) -> None:
        """
        Apply a backend-validated recharge credit.
        Called by ValidateToken use-case after a successful API response.
        """
        if kwh <= 0:
            raise ValueError("Credit must be a positive value (got {})".format(kwh))
        self._kwh += float(kwh)

    def apply_consumption(self, reading) -> None:
        """
        Deduct metered consumption from the balance.
        reading: EnergyReading value object (delta_kwh field used).
        Balance is clamped to 0.0 — never goes negative.
        """
        self._kwh = max(0.0, self._kwh - reading.delta_kwh)

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def balance_kwh(self) -> float:
        """Current balance rounded to 3 decimal places."""
        return round(self._kwh, 3)

    @property
    def state(self) -> str:
        """Derived supply state based on current balance."""
        if self._kwh <= 0.0:
            return NO_CREDIT
        if self._kwh < _WARNING_KWH:
            return WARNING
        return CREDIT

    @property
    def supply_active(self) -> bool:
        """True when the relay should be closed (power flowing)."""
        return self._kwh > 0.0

    def __repr__(self) -> str:
        return "Meter(state={}, kwh={})".format(self.state, self.balance_kwh)
