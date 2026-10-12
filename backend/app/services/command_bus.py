from dataclasses import dataclass


@dataclass
class CommandResult:
    accepted: bool
    message: str


class MockCommandBus:
    """
    Development-only command bus.

    This intentionally does not contain RS485/Modbus code.
    Later this class can be replaced by an MQTT-based command bus.
    """

    async def publish(self, device: str, payload: dict) -> CommandResult:
        return CommandResult(True, f"Mock command accepted for {device}")


command_bus = MockCommandBus()
