# app/domain/value_objects/energy_reading.py
# Immutable value object — snapshot from one energy sensor poll.


class EnergyReading:
    """
    Immutable snapshot of one energy measurement cycle.

    Fields
    ------
    voltage_v  : line voltage in Volts
    current_a  : current draw in Amperes
    power_w    : instantaneous active power in Watts
    delta_kwh  : energy consumed since the previous reading (kWh)
    """

    __slots__ = ("voltage_v", "current_a", "power_w", "delta_kwh")

    def __init__(self,
                 voltage_v: float,
                 current_a: float,
                 power_w: float,
                 delta_kwh: float):
        self.voltage_v = voltage_v
        self.current_a = current_a
        self.power_w   = power_w
        self.delta_kwh = delta_kwh

    def __repr__(self) -> str:
        return (
            "EnergyReading(V={:.1f}, A={:.3f}, W={:.1f}, Δkwh={:.6f})"
            .format(self.voltage_v, self.current_a,
                    self.power_w, self.delta_kwh)
        )
