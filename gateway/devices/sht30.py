from dataclasses import dataclass
<<<<<<< HEAD
from ..modbus.client import ModbusRTU, ModbusError

=======

from ..modbus.client import ModbusRTU, ModbusError


>>>>>>> Rac
@dataclass
class SHT30Reading:
    temperature: float
    humidity: float
<<<<<<< HEAD

class SHT30:
    def __init__(self, bus: ModbusRTU, slave_id: int):
        self.bus = bus
        self.slave_id = slave_id
=======
    raw: tuple = ()


class SHT30:
    """RS485 SHT30 module (TH10S-B-PE). The register map is configurable
    because it differs between vendors; defaults are an unverified guess."""

    def __init__(self, bus: ModbusRTU, slave_id: int, function: int = 0x03,
                 temp_reg: int = 0, hum_reg: int = 1, scale: float = 10.0):
        self.bus = bus
        self.slave_id = slave_id
        self.function = function
        self.temp_reg = temp_reg
        self.hum_reg = hum_reg
        self.scale = scale
>>>>>>> Rac

    @staticmethod
    def signed_int16(value: int) -> int:
        return value - 0x10000 if value & 0x8000 else value

    def read(self) -> SHT30Reading:
<<<<<<< HEAD
        registers = self.bus.read_holding_registers(self.slave_id, 0x0000, 2)
        temperature_raw = self.signed_int16(registers[0])
        humidity_raw = registers[1]
        if temperature_raw == -32768 or humidity_raw == 0x8000:
            raise ModbusError("SHT30 reports invalid/no-data value")
        return SHT30Reading(temperature_raw / 10.0, humidity_raw / 10.0)
=======
        start = min(self.temp_reg, self.hum_reg)
        count = abs(self.temp_reg - self.hum_reg) + 1
        regs = self.bus.read_registers(self.slave_id, start, count, self.function)
        temperature_raw = self.signed_int16(regs[self.temp_reg - start])
        humidity_raw = regs[self.hum_reg - start]
        if temperature_raw == -32768 or humidity_raw == 0x8000:
            raise ModbusError("SHT30 reports invalid/no-data value")
        temperature = temperature_raw / self.scale
        humidity = humidity_raw / self.scale
        if not (-40.0 <= temperature <= 85.0) or not (0.0 <= humidity <= 100.5):
            raise ModbusError(
                f"Implausible reading T={temperature} H={humidity} "
                f"(raw {temperature_raw}/{humidity_raw}) - check TH_* register map"
            )
        return SHT30Reading(temperature, humidity, (temperature_raw, humidity_raw))
>>>>>>> Rac
