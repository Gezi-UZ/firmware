# app/application/use_cases/process_energy_reading.py
# Single Responsibility: read sensor → update Meter balance.


class ProcessEnergyReading:
    """
    Use-case: poll the energy monitor and deduct consumption from the Meter.

    Dependencies (injected via constructor — DIP):
      monitor : IEnergyMonitor
      meter   : Meter
    """

    def __init__(self, monitor, meter):
        self._monitor = monitor
        self._meter   = meter

    def execute(self) -> None:
        """
        Called every main-loop iteration (~100 ms).
        monitor.read() is non-blocking and returns None when the
        polling interval hasn't elapsed yet.
        """
        reading = self._monitor.read()
        if reading is not None:
            self._meter.apply_consumption(reading)
