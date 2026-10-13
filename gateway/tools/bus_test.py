r"""Reproduce what the gateway does on the bus, and count failures per step.

For every FRAME_GAP value it repeats: read TH -> read light -> relay ON -> relay OFF
(no retries), so you can see WHICH step fails and whether a longer silence between
frames fixes it. WARNING: it switches relay channel 2 on and off (no load needed).

Stop the gateway first (only one program may use the COM port):

    python gateway\tools\bus_test.py --port COM6
    python gateway\tools\bus_test.py --port COM6 --gaps 0.006,0.05,0.1,0.2 --rounds 10
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from modbus.client import ModbusRTU, ModbusError  # noqa: E402


def attempt(fn):
    try:
        fn()
        return True, ""
    except ModbusError as exc:
        return False, str(exc)


def main():
    parser = argparse.ArgumentParser(description="Gateway-like bus stress test")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--th", type=int, default=1)
    parser.add_argument("--light", type=int, default=2)
    parser.add_argument("--relay", type=int, default=3)
    parser.add_argument("--channel", type=int, default=2, choices=(1, 2), help="relay channel to switch (1 or 2)")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--gaps", default="0.006,0.05,0.1,0.2", help="comma separated silence values in seconds")
    args = parser.parse_args()

    bus = ModbusRTU(args.port, args.baud, 0.4)
    if not hasattr(bus, "frame_gap"):
        sys.exit("gateway/modbus/client.py is the OLD version. Replace it with the new client.py first.")
    bus.retries = 0
    bus.open()
    coil = args.channel - 1
    rows = []
    last_errors = {}
    try:
        for gap in [float(x) for x in args.gaps.split(",")]:
            bus.frame_gap = gap
            ok = {"TH read": 0, "light read": 0, "relay ON": 0, "relay OFF": 0}
            for _ in range(args.rounds):
                steps = (
                    ("TH read", lambda: bus.read_registers(args.th, 0, 2)),
                    ("light read", lambda: bus.read_registers(args.light, 2, 2)),
                    ("relay ON", lambda: bus.write_single_coil(args.relay, coil, True)),
                    ("relay OFF", lambda: bus.write_single_coil(args.relay, coil, False)),
                )
                for name, fn in steps:
                    good, message = attempt(fn)
                    ok[name] += good
                    if not good:
                        last_errors[name] = message
                    if name == "relay ON":
                        time.sleep(0.3)
            rows.append((gap, ok))
    finally:
        try:
            bus.write_single_coil(args.relay, coil, False)  # leave the relay OFF
        except ModbusError:
            pass
        bus.close()

    print(f"\nresults: successes out of {args.rounds} rounds")
    print(f"{'gap (s)':>8} | {'TH read':>8} | {'light read':>10} | {'relay ON':>9} | {'relay OFF':>9}")
    for gap, ok in rows:
        print(f"{gap:>8} | {ok['TH read']:>8} | {ok['light read']:>10} | {ok['relay ON']:>9} | {ok['relay OFF']:>9}")
    if last_errors:
        print("\nlast error per step:")
        for name, message in last_errors.items():
            print(f"  {name}: {message}")
    print("""
How to read it:
  * Relay ON fails but OFF works at every gap  -> not timing: power dip when the coil pulls in, or the board.
  * Relay fails at small gaps, fine at larger  -> timing: set FRAME_GAP in gateway/.env to the smallest good value (x2).
  * Everything fails, including reads          -> wiring/power on the bus, not the relay.
  * Everything works                            -> the problem is in the gateway/web side; send me the gateway log.""")


if __name__ == "__main__":
    main()
