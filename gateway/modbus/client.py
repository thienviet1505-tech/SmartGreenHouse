import os
import threading
import time
<<<<<<< HEAD
=======

>>>>>>> Rac
import serial


class ModbusError(RuntimeError):
    pass


class ModbusRTU:
<<<<<<< HEAD
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.8):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.lock = threading.RLock()

=======
    """Minimal Modbus RTU master (FC01/03/04/05/06) over a serial port."""

    # Modbus RTU needs >= 3.5 character times of silence between frames
    # (~4 ms at 9600 baud). Some relay boards need much more, because they also
    # hear the other devices' replies on the shared bus, so the default is
    # generous. Tune with FRAME_GAP (seconds) and MODBUS_RETRIES in gateway/.env.
    DEFAULT_FRAME_GAP = 0.05
    DEFAULT_RETRIES = 2
    # pyserial's read(n) blocks until n bytes arrive OR the serial timeout
    # expires. Keep the serial timeout short and enforce the real deadline
    # (self.timeout) ourselves, otherwise every request costs the full timeout.
    SERIAL_POLL = 0.02

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.8):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout  # whole-request deadline
        self.serial = None
        self.lock = threading.RLock()
        self._last_activity = 0.0
        self.frame_gap = float(os.getenv("FRAME_GAP", self.DEFAULT_FRAME_GAP))
        self.retries = int(os.getenv("MODBUS_RETRIES", self.DEFAULT_RETRIES))  # writes only

    # ---------------------------------------------------------------- CRC
>>>>>>> Rac
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

<<<<<<< HEAD
    def open(self):
        self.serial = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=self.timeout, write_timeout=self.timeout)
=======
    # --------------------------------------------------------------- port
    def open(self):
        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            serial.EIGHTBITS,
            serial.PARITY_NONE,
            serial.STOPBITS_ONE,
            timeout=self.SERIAL_POLL,
            write_timeout=self.timeout,
        )
>>>>>>> Rac

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

    def _ensure_open(self):
        if self.serial is None or not self.serial.is_open:
            raise ModbusError("RS485 serial port is not open")

<<<<<<< HEAD
    def _transact(self, request: bytes, slave: int, function: int) -> bytes:
        with self.lock:
            self._ensure_open()
=======
    def _wait_gap(self):
        wait = self.frame_gap - (time.monotonic() - self._last_activity)
        if wait > 0:
            time.sleep(wait)

    # ---------------------------------------------------------- transport
    def _complete_frame(self, response: bytearray, slave: int, function: int):
        """Return the full frame once received, None while incomplete."""
        if len(response) < 5:
            return None
        if response[0] != slave:
            raise ModbusError(f"Unexpected slave ID {response[0]} (expected {slave})")
        code = response[1]
        if code == (function | 0x80):
            frame = bytes(response[:5])
            if not self.valid_crc(frame):
                raise ModbusError("Invalid Modbus CRC")
            raise ModbusError(f"Modbus exception 0x{frame[2]:02X}")
        if code != function:
            raise ModbusError(f"Unexpected function 0x{code:02X} (expected 0x{function:02X})")
        expected = 5 + response[2] if function in (0x01, 0x02, 0x03, 0x04) else 8
        if len(response) < expected:
            return None
        frame = bytes(response[:expected])
        if not self.valid_crc(frame):
            raise ModbusError("Invalid Modbus CRC")
        return frame

    def _transact(self, request: bytes, slave: int, function: int, retries: int = 0) -> bytes:
        """One request/response. Only timeouts and CRC errors are retried
        (and only for idempotent writes); Modbus exceptions are final."""
        last_error = None
        for _ in range(retries + 1):
            try:
                return self._transact_once(request, slave, function)
            except ModbusError as exc:
                last_error = exc
                if "Timeout" not in str(exc) and "CRC" not in str(exc):
                    raise
        raise last_error

    def _transact_once(self, request: bytes, slave: int, function: int) -> bytes:
        with self.lock:
            self._ensure_open()
            self._wait_gap()
>>>>>>> Rac
            self.serial.reset_input_buffer()
            self.serial.write(request)
            self.serial.flush()
            deadline = time.monotonic() + self.timeout
            response = bytearray()
<<<<<<< HEAD
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
=======
            try:
                while time.monotonic() < deadline:
                    chunk = self.serial.read(self.serial.in_waiting or 1)
                    if not chunk:
                        continue
                    response.extend(chunk)
                    frame = self._complete_frame(response, slave, function)
                    if frame is not None:
                        return frame
                raise ModbusError(f"Timeout waiting for slave {slave}, function 0x{function:02X}")
            finally:
                self._last_activity = time.monotonic()

    def raw_exchange(self, request: bytes, wait: float = 0.5) -> bytes:
        """Send raw bytes and return whatever comes back (used by tools only)."""
        with self.lock:
            self._ensure_open()
            self._wait_gap()
            self.serial.reset_input_buffer()
            self.serial.write(request)
            self.serial.flush()
            end = time.monotonic() + wait
            out = bytearray()
            while time.monotonic() < end:
                chunk = self.serial.read(self.serial.in_waiting or 1)
                if chunk:
                    out.extend(chunk)
                    end = min(end, time.monotonic() + 0.05)
            self._last_activity = time.monotonic()
            return bytes(out)

    # ----------------------------------------------------------- requests
    def read_registers(self, slave: int, address: int, count: int, function: int = 0x03):
        if function not in (0x03, 0x04):
            raise ValueError("function must be 0x03 or 0x04")
        payload = bytes([slave, function, address >> 8, address & 0xFF, count >> 8, count & 0xFF])
        response = self._transact(self.frame(payload), slave, function)
>>>>>>> Rac
        raw = response[3:3 + response[2]]
        if len(raw) != count * 2:
            raise ModbusError(f"Unexpected register byte count: {len(raw)}")
        return [(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw), 2)]

<<<<<<< HEAD
=======
    def read_holding_registers(self, slave: int, address: int, count: int):
        return self.read_registers(slave, address, count, 0x03)

    def read_input_registers(self, slave: int, address: int, count: int):
        return self.read_registers(slave, address, count, 0x04)

    def read_coils(self, slave: int, address: int, count: int):
        payload = bytes([slave, 0x01, address >> 8, address & 0xFF, count >> 8, count & 0xFF])
        response = self._transact(self.frame(payload), slave, 0x01)
        bits = response[3:3 + response[2]]
        if len(bits) < (count + 7) // 8:
            raise ModbusError(f"Unexpected coil byte count: {len(bits)}")
        return [bool((bits[i // 8] >> (i % 8)) & 1) for i in range(count)]

>>>>>>> Rac
    def write_single_register(self, slave: int, address: int, value: int):
        payload = bytes([slave, 0x06, address >> 8, address & 0xFF, value >> 8, value & 0xFF])
        self._transact(self.frame(payload), slave, 0x06, retries=self.retries)

    def write_single_coil(self, slave: int, address: int, on: bool):
        value = 0xFF00 if on else 0x0000
        payload = bytes([slave, 0x05, address >> 8, address & 0xFF, value >> 8, value & 0xFF])
        self._transact(self.frame(payload), slave, 0x05, retries=self.retries)
