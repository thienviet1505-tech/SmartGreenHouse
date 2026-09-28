# Windows Hardware Gateway

This folder is the physical-device side of the greenhouse system.

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r gateway\requirements.txt
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
