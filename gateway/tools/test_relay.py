r"""Relay diagnostic tool. WARNING: it SWITCHES the relay on and off - do not
connect a mains load while testing (use nothing, or a small 12V load).

Frames follow the vendor documents of the 2-channel RS485 relay modules with
an STM32F030F4 (icdayroi / vietnic / EPCB). Default address of those modules is
1 (some batches: 255), default baud 9600 8N1.

    python gateway\tools\test_relay.py --port COM6
    python gateway\tools\test_relay.py --port COM6 --ids 1,255,3 --baud 9600

Step 1  asks the relay for its own address (broadcast address 0, read-only).
Step 2  switches channel 1 and 2 on/off at each address with FC05 and prints
        the reply. A working relay echoes the request and CLICKS.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from modbus.client import ModbusRTU  # noqa: E402


def hx(data: bytes) -> str:
    return data.hex(" ").upper() if data else "(no reply)"


def main():
    parser = argparse.ArgumentParser(description="Relay click test")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--ids", default="1,255", help="addresses to try, e.g. 1,255,3")
    parser.add_argument("--hold", type=float, default=1.5, help="seconds each channel stays ON")
    args = parser.parse_args()

    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    bus = ModbusRTU(args.port, args.baud, 0.5)
    bus.open()
    worked = []
    try:
        print("=== Step 1: address query (broadcast, read-only) ===")
        query = ModbusRTU.frame(bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x01]))
        print("sent :", hx(query))
        print("reply:", hx(bus.raw_exchange(query, 0.6)))

        print("\n=== Step 2: click test (FC05) ===")
        for slave in ids:
            for channel in (0, 1):
                on = ModbusRTU.frame(bytes([slave, 0x05, 0x00, channel, 0xFF, 0x00]))
                off = ModbusRTU.frame(bytes([slave, 0x05, 0x00, channel, 0x00, 0x00]))
                print(f"\naddress {slave}, channel {channel + 1}: ON  -> sent {hx(on)}")
                reply_on = bus.raw_exchange(on, 0.4)
                print("  reply:", hx(reply_on))
                time.sleep(args.hold)
                reply_off = bus.raw_exchange(off, 0.4)
                print("  OFF reply:", hx(reply_off))
                if reply_on == on:
                    worked.append((slave, channel + 1))
    finally:
        bus.close()

    print("\n=== summary ===")
    if worked:
        for slave, channel in worked:
            print(f"address {slave} channel {channel}: relay echoed the command (it answers here)")
        print("Set RELAY_ID in gateway/.env to the address that answered.")
    else:
        print("No echo received. Listen/look anyway: if the relay clicked, it works without echoing.")
        print("If nothing clicked: swap A/B, check the RS485/UART jumper, 12V power, try --baud 4800 / 19200.")


if __name__ == "__main__":
    main()
