from dataclasses import dataclass
from ..modbus.client import ModbusRTU

@dataclass
class LightReading:
    lux: float

class SEN0644:
    def __init__(self, bus: ModbusRTU, slave_id: int):
        self.bus = bus
        self.slave_id = slave_id

    def read(self) -> LightReading:
        registers = self.bus.read_holding_registers(self.slave_id, 0x0002, 2)
        raw = (registers[0] << 16) | registers[1]
        return LightReading(raw / 1000.0)
