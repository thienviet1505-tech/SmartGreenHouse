import argparse
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from modbus.client import ModbusRTU


def main():
    parser = argparse.ArgumentParser(description="Change DFRobot SEN0644 Modbus slave ID")
    parser.add_argument("--port", required=True)
    parser.add_argument("--old-id", type=int, default=1)
    parser.add_argument("--new-id", type=int, required=True)
    args = parser.parse_args()
    print("WARNING: connect ONLY the SEN0644 to this RS485 bus.")
    print("Do not connect the SHT30 while both devices still use address 1.")
    input("Press Enter to continue...")
    bus = ModbusRTU(args.port, 9600, 1.0)
    bus.open()
    try:
        bus.write_single_register(args.old_id, 0x0064, args.new_id)
        print(f"SEN0644 address changed: {args.old_id} -> {args.new_id}")
        print("Power-cycle the SEN0644 before normal operation.")
    finally:
        bus.close()

if __name__ == "__main__":
    main()
