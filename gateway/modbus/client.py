import threading
import time
import serial


class ModbusError(RuntimeError):
    pass


class ModbusRTU:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.8):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.lock = threading.RLock()

    @staticmethod
    def crc16(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = ((crc >> 1) ^ 0xA001) if crc & 1 else (crc >> 1)
        return crc & 0xFFFF

    @classmethod
    def frame(cls, payload: bytes) -> bytes:
        crc = cls.crc16(payload)
        return payload + bytes((crc & 0xFF, (crc >> 8) & 0xFF))

    @classmethod
    def valid_crc(cls, frame: bytes) -> bool:
        if len(frame) < 4:
            return False
        received = frame[-2] | (frame[-1] << 8)
        return received == cls.crc16(frame[:-2])

    def open(self):
        self.serial = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=self.timeout, write_timeout=self.timeout)

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

    def _ensure_open(self):
        if self.serial is None or not self.serial.is_open:
            raise ModbusError("RS485 serial port is not open")

    def _transact(self, request: bytes, slave: int, function: int) -> bytes:
        with self.lock:
            self._ensure_open()
            self.serial.reset_input_buffer()
            self.serial.write(request)
            self.serial.flush()
            deadline = time.monotonic() + self.timeout
            response = bytearray()
            while time.monotonic() < deadline:
                chunk = self.serial.read(256)
                if chunk:
                    response.extend(chunk)
                    if len(response) >= 5:
                        if response[0] != slave:
                            raise ModbusError(f"Unexpected slave ID {response[0]} != {slave}")
                        if response[1] == function:
                            if function == 0x03:
                                expected_len = 5 + response[2]
                                if len(response) >= expected_len:
                                    frame = bytes(response[:expected_len])
                                    if not self.valid_crc(frame):
                                        raise ModbusError("Invalid Modbus CRC")
                                    return frame
                            else:
                                if len(response) >= 8:
                                    frame = bytes(response[:8])
                                    if not self.valid_crc(frame):
                                        raise ModbusError("Invalid Modbus CRC")
                                    return frame
                        elif response[1] == (function | 0x80) and len(response) >= 5:
                            frame = bytes(response[:5])
                            if not self.valid_crc(frame):
                                raise ModbusError("Invalid Modbus CRC")
                            raise ModbusError(f"Modbus exception 0x{frame[2]:02X}")
            raise ModbusError(f"Timeout waiting for slave {slave}, function 0x{function:02X}")

    def read_holding_registers(self, slave: int, address: int, count: int):
        payload = bytes([slave, 0x03, address >> 8, address & 0xFF, count >> 8, count & 0xFF])
        response = self._transact(self.frame(payload), slave, 0x03)
        raw = response[3:3 + response[2]]
        if len(raw) != count * 2:
            raise ModbusError(f"Unexpected register byte count: {len(raw)}")
        return [(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw), 2)]

    def write_single_register(self, slave: int, address: int, value: int):
        payload = bytes([slave, 0x06, address >> 8, address & 0xFF, value >> 8, value & 0xFF])
        self._transact(self.frame(payload), slave, 0x06)

    def write_single_coil(self, slave: int, address: int, on: bool):
        value = 0xFF00 if on else 0x0000
        payload = bytes([slave, 0x05, address >> 8, address & 0xFF, value >> 8, value & 0xFF])
        self._transact(self.frame(payload), slave, 0x05)
