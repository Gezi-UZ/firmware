# app/domain/ports/i_relay.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class IRelay:
    """
    Abstract port for relay control.

    Active-low vs active-high polarity is an implementation detail
    that belongs in the concrete adapter, not here.
    """

    def update(self, meter) -> None:
        """
        Set the relay state based on meter.supply_active.
        Closes the relay (power ON) when supply_active is True.
        Opens the relay (power OFF) when supply_active is False.
        """
        raise NotImplementedError
