r"""Change the Modbus address of the 2-channel relay board.

The frame (broadcast address 0x00, FC 0x10, register 0x0000 = new address) is
taken from the vendor documentation of the RS485 relay modules of this family
(EPCB / icdayroi), NOT from a datasheet of your exact board. It is verified
afterwards by reading the coils at the new address. If your board's manual
describes a different procedure, follow the manual instead.

IMPORTANT: connect ONLY the relay board to the RS485 bus while doing this
(a broadcast frame is received by every device on the bus).

    python gateway\tools\set_relay_id.py --port COM5 --new-id 3 --dry-run
    python gateway\tools\set_relay_id.py --port COM5 --new-id 3
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from modbus.client import ModbusRTU, ModbusError  # noqa: E402


def build_frame(new_id: int) -> bytes:
    return ModbusRTU.frame(bytes([0x00, 0x10, 0x00, 0x00, 0x00, 0x01, 0x02, 0x00, new_id]))


def main():
    parser = argparse.ArgumentParser(description="Change relay board Modbus address")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--new-id", type=int, required=True, help="1..247")
    parser.add_argument("--dry-run", action="store_true", help="only print the frame")
    args = parser.parse_args()

    if not 1 <= args.new_id <= 247:
        sys.exit("new-id must be 1..247 (never use 255 on a shared bus)")

    frame = build_frame(args.new_id)
    print("Frame to broadcast:", frame.hex(" ").upper())
    if args.dry_run:
        return

    print("WARNING: only the relay board may be connected to the RS485 bus.")
    if input("Type YES to continue: ").strip() != "YES":
        sys.exit("Cancelled.")

    bus = ModbusRTU(args.port, args.baud, 0.8)
    bus.open()
    try:
        reply = bus.raw_exchange(frame, wait=0.8)
        print("Raw reply:", reply.hex(" ").upper() if reply else "(none)")
        time.sleep(0.5)
        confirmed = None
        try:  # many of these boards do not implement FC01, so FC05 is the fallback
            confirmed = f"coils={bus.read_coils(args.new_id, 0, 2)}"
        except ModbusError:
            try:
                bus.write_single_coil(args.new_id, 0, False)  # harmless: channel 1 OFF
                confirmed = "channel 1 OFF acknowledged"
            except ModbusError as exc:
                print(f"Could not confirm the new address: {exc}")
        if confirmed:
            print(f"OK: relay now answers at address {args.new_id} ({confirmed}).")
            print("Set RELAY_ID in gateway/.env to this value.")
        else:
            print("Try: power-cycle the relay board and run test_relay.py --ids 1,255,%d;" % args.new_id)
            print("if nothing changes, use the procedure in your board's manual.")
    finally:
        bus.close()


if __name__ == "__main__":
    main()
