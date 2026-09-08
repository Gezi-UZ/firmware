# Single Responsibility: read sensor → update Meter balance.


class ProcessEnergyReading:
    """
    Use-case: poll the energy monitor and deduct consumption from the Meter.

    Dependencies (injected via constructor — DIP):
      monitor : IEnergyMonitor
      meter   : Meter
    Use-case: poll the energy monitor and deduct consumption from the Meter(s).
    Only deducts consumption when supply is active (relay closed).
    Stores latest readings for telemetry.
    """

    def __init__(self, monitor, meter, repo): # pyright: ignore[reportRedeclaration]
        self._monitor = monitor
        self._meter   = meter
        self._repo    = repo
    def __init__(self, monitor, meter_c0, repo_c0, meter_c1=None, repo_c1=None):
        self._monitor  = monitor
        self._meter_c0 = meter_c0
        self._repo_c0  = repo_c0
        self._meter_c1 = meter_c1
        self._repo_c1  = repo_c1
        self.last_reading_c0 = None
        self.last_reading_c1 = None

    def execute(self) -> None:
        """
        Called every main-loop iteration (~100 ms).
        monitor.read() is non-blocking and returns None when the
        polling interval hasn't elapsed yet.
        Polls non-blocking monitor for active channels.
        """
        reading = self._monitor.read()
        if reading is not None:
            self._meter.apply_consumption(reading)
            # Try to save to flash (Adapter handles wear-leveling)
            self._repo.save(self._meter.balance_kwh, force=False)
        # Channel 0
        if self._meter_c0.supply_active:
            reading_0 = self._monitor.read(channel=0)
            if reading_0 is not None:
                self.last_reading_c0 = reading_0
                self._meter_c0.apply_consumption(reading_0)
                self._repo_c0.save(self._meter_c0.balance_kwh, force=False)

        # Channel 1
        if self._meter_c1 and self._meter_c1.supply_active:
            reading_1 = self._monitor.read(channel=1)
            if reading_1 is not None:
                self.last_reading_c1 = reading_1
                self._meter_c1.apply_consumption(reading_1)
                if self._repo_c1:
                    self._repo_c1.save(self._meter_c1.balance_kwh, force=False)

