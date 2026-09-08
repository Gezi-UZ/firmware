# app/domain/ports/i_energy_monitor.py
# Port interface — ISP: Interface Segregation + DIP: Dependency Inversion


class IEnergyMonitor:
    """
    Abstract port for energy measurement.

    read() must be non-blocking. The implementation is responsible for
    rate-limiting reads (e.g. only polling the PZEM sensor once per second).
    """

    def read(self, channel: int = 0):
        """
        Return an EnergyReading value object if a new reading is available,
        or None if the polling interval has not yet elapsed.
        Must be non-blocking. Supports dual channels.
        """
        raise NotImplementedError

