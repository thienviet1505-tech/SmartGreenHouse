from ..modbus.client import ModbusRTU


class Relay2CH:
    def __init__(self, bus: ModbusRTU, slave_id: int):
        self.bus = bus
        self.slave_id = slave_id
        self.states = {0: False, 1: False}

    def set_channel(self, channel: int, state: bool):
        if channel not in (0, 1):
            raise ValueError("Relay channel must be 0 or 1")
        self.bus.write_single_coil(self.slave_id, channel, state)
        self.states[channel] = state

    def initialize_off(self):
        """Force both channels OFF so hardware and software states agree."""
        for channel in (0, 1):
            self.set_channel(channel, False)

    def restore(self):
        """Re-send the software states to the hardware. Used as a connectivity
        probe after a failure, and it makes the relay match the software again
        if the relay board lost power in the meantime."""
        for channel in (0, 1):
            self.set_channel(channel, self.states[channel])
