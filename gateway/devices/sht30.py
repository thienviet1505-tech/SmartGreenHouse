from dataclasses import dataclass
from ..modbus.client import ModbusRTU, ModbusError

@dataclass
class SHT30Reading:
    temperature: float
    humidity: float

class SHT30:
    def __init__(self, bus: ModbusRTU, slave_id: int):
        self.bus = bus
        self.slave_id = slave_id

    @staticmethod
    def signed_int16(value: int) -> int:
        return value - 0x10000 if value & 0x8000 else value

    def read(self) -> SHT30Reading:
        registers = self.bus.read_holding_registers(self.slave_id, 0x0000, 2)
        temperature_raw = self.signed_int16(registers[0])
        humidity_raw = registers[1]
        if temperature_raw == -32768 or humidity_raw == 0x8000:
            raise ModbusError("SHT30 reports invalid/no-data value")
        return SHT30Reading(temperature_raw / 10.0, humidity_raw / 10.0)
