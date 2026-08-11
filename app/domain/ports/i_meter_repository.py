# Interface for persisting the meter's balance.

class IMeterRepository:
    def load(self) -> float:
        """
        Loads the persisted kWh balance. 
        Should return 0.0 if no prior state exists.
        """
        raise NotImplementedError()

    def save(self, current_kwh: float, force: bool = False) -> None:
        """
        Requests to save the current balance.
        If force=True (e.g., after a recharge), the implementation MUST save immediately.
        If force=False (e.g., during normal consumption), the implementation may 
        throttle saves to prevent flash memory wear.
        """
        raise NotImplementedError()
