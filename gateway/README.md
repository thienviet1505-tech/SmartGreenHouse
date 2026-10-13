# Windows Hardware Gateway

<<<<<<< HEAD
This folder is the physical-device side of the greenhouse system.
=======
Physical-device side of the greenhouse system (USB-RS485, Modbus RTU, local AUTO control).
>>>>>>> Rac

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r gateway\requirements.txt
<<<<<<< HEAD
```

Copy:

```text
gateway\.env.example -> gateway\.env
```

Set your real COM port, e.g. `COM5`.

## Modbus addresses

The intended bus is:

```text
SHT30   = 1
SEN0644 = 2
Relay   = 255
```

SHT30 and SEN0644 both factory-default to address 1. Therefore change the SEN0644 to address 2 **while it is the only device on the RS485 bus**:

```powershell
python gateway\tools\set_light_id.py --port COM5 --old-id 1 --new-id 2
```

Power-cycle the SEN0644 after changing the address.

## Run

Start Web backend first:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Then:

```powershell
python gateway\gateway.py
```

The same `GATEWAY_TOKEN` must be set in the web `.env` and `gateway\.env`.

## Laptop logs

When the Web sends:

```text
FAN -> ON
```

the laptop prints:

```text
[WEB COMMAND] FAN -> ON | CH1 | reason=manual control from website
```

and writes the log to:

```text
gateway\gateway.log
```

AUTO actions are also logged, for example:

```text
[AUTO] FAN -> ON | CH1 | reason=temperature=30.4°C
```

## Public server

For a public HTTPS deployment use:

```text
WEB_WS_URL=wss://your-domain.com/ws/gateway
```

The laptop makes an outbound WebSocket connection, so the laptop does not need an inbound router port.
=======
copy gateway\.env.example gateway\.env
```

Edit `gateway\.env`: real COM port, `GATEWAY_TOKEN` (same as the root `.env`).

## Modbus address plan (all devices 9600 8N1)

| Device | Address | How to set it |
|---|---|---|
| TH10S-B-PE (SHT30) temperature/humidity | **1** | EPCB PC app (address can only be set by software). Usually already 1. |
| DFRobot SEN0644 light sensor | **2** | `tools\set_light_id.py` (default is 1) |
| 2-channel relay | **3** | `tools\set_relay_id.py` (see warning below) |

Never use **255** on a shared bus: the SEN0644 treats 0xFF as its "general address", so
a command sent to 255 would also be seen by the light sensor (collisions / wrong replies).

### Procedure - connect ONE device at a time while changing addresses

1. **Relay only** on the bus:
   `python gateway\tools\probe_modbus.py --port COM5 --ids 1,255` -> shows the address it answers on (FC01 coils).
   Then `python gateway\tools\set_relay_id.py --port COM5 --new-id 3` (use `--dry-run` first).
   If your relay's manual describes a different procedure, follow the manual.
2. **SEN0644 only**: `python gateway\tools\set_light_id.py --port COM5 --old-id 1 --new-id 2`, then power-cycle it.
3. **TH10S-B-PE only**: `python gateway\tools\probe_modbus.py --port COM5 --ids 1`.
   Read the printed registers (breathe on the sensor: humidity jumps up) and set `TH_FUNCTION`,
   `TH_TEMP_REG`, `TH_HUM_REG`, `TH_SCALE` in `gateway\.env` according to the vendor PDF.
4. **All three connected**: `python gateway\tools\probe_modbus.py --port COM5 --ids 1,2,3`.

## Run

Start the web backend first (`run_web.bat`), then:

```powershell
run_gateway.bat
```
or `python -m gateway.gateway` from the project root. (`python gateway\gateway.py` does NOT work: the
modules use package-relative imports.)

At start-up the gateway forces both relays OFF so the hardware and software states agree.

## Behaviour notes

* Each sensor is read independently. A sensor that fails or is older than `SENSOR_STALE_SECONDS` is
  ignored by AUTO control (its output keeps the current state); the other sensor keeps working.
* With no complete sensor reading yet, the gateway reports link status only, so the website shows the
  RS485 error instead of looking disconnected.
* The website pushes its saved AUTO thresholds to the gateway every time the gateway connects.

## Laptop logs

`[WEB COMMAND] FAN -> ON | CH1 | reason=manual control from website` and
`[AUTO] FAN -> ON | CH1 | reason=temperature=30.4°C` are printed and written to `gateway\gateway.log`.

## Public server

```text
WEB_WS_URL=wss://your-domain.com/ws/gateway
```
The laptop opens an outbound connection, so no inbound router port is needed for the gateway.
>>>>>>> Rac
