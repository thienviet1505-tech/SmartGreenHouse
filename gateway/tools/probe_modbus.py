r"""READ-ONLY scanner: find which Modbus address each device answers on and
which register map it uses. Sends only read requests (FC01/03/04).

Usage (from the project root, with the venv active):
    python gateway\tools\probe_modbus.py --port COM5
    python gateway\tools\probe_modbus.py --port COM5 --ids 1,2,3,255 --baud 9600

Tip: connect ONE device at a time when you do not know their addresses
(several devices answering the same address would collide on the bus).
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from modbus.client import ModbusRTU, ModbusError  # noqa: E402


def parse_ids(text):
    ids = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ids.extend(range(int(a), int(b) + 1))
        elif part:
            ids.append(int(part))
    return ids


def describe_regs(label, regs):
    if label == "light":
        raw = (regs[0] << 16) | regs[1]
        return f"regs={regs}  -> 32-bit/1000 = {raw / 1000:.3f} lux (SEN0644 style)"
    signed = [r - 0x10000 if r & 0x8000 else r for r in regs]
    return f"regs={regs}  -> /10 = {[s / 10 for s in signed]}"


TESTS = [
    ("FC03 reg 0x0000 x2", "regs", lambda b, i: b.read_registers(i, 0x0000, 2, 0x03)),
    ("FC04 reg 0x0000 x2", "regs", lambda b, i: b.read_registers(i, 0x0000, 2, 0x04)),
    ("FC03 reg 0x0002 x2", "light", lambda b, i: b.read_registers(i, 0x0002, 2, 0x03)),
    ("FC03 reg 0x07D0 x2", "regs", lambda b, i: b.read_registers(i, 0x07D0, 2, 0x03)),
    ("FC01 coils 0..1   ", "coils", lambda b, i: b.read_coils(i, 0, 2)),
]


def main():
    parser = argparse.ArgumentParser(description="Read-only Modbus RTU probe")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--ids", default="1,2,3,255", help="e.g. 1,2,3,255 or 1-10")
    parser.add_argument("--timeout", type=float, default=0.4)
    args = parser.parse_args()

    bus = ModbusRTU(args.port, args.baud, args.timeout)
    bus.open()
    answered = {}
    try:
        for slave in parse_ids(args.ids):
            print(f"\n=== slave {slave} ===")
            for name, label, call in TESTS:
                try:
                    result = call(bus, slave)
                    text = f"coils={result}" if label == "coils" else describe_regs(label, result)
                    print(f"  OK       {name}: {text}")
                    answered.setdefault(slave, []).append(name.strip())
                except ModbusError as exc:
                    print(f"  --       {name}: {exc}")
    finally:
        bus.close()

    print("\n=== summary ===")
    if not answered:
        print("No device answered. Check: COM port, A/B wires (try swapping), 12V power, baud rate, address.")
    for slave, names in answered.items():
        print(f"slave {slave} answered: {', '.join(names)}")
    print("""
How to read it:
  * Temperature/humidity sensor: a register pair around 200-350 (=20-35 C) and 300-900 (=30-90 %RH).
    Breathe on the sensor: the humidity register jumps up. That tells you which register is which,
    then set TH_FUNCTION / TH_TEMP_REG / TH_HUM_REG in gateway/.env.
  * Light sensor (SEN0644): the 0x0002 pair gives lux. Cover it with your hand: the value drops.
  * Relay: FC01 coils answer = it is the relay (and that is its address).""")


if __name__ == "__main__":
    main()
