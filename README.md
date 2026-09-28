# Smart Greenhouse Web

Web/cloud side of the smart greenhouse project.

## Scope

This project intentionally contains **no RS485/Modbus hardware code**.

The future hardware side will be a separate Windows Gateway:

```text
gateway/
    RS485 + Modbus RTU
    SHT30
    DFRobot SEN0644
    Relay 2CH
    Local AUTO control
    MQTT/HTTP client
```

The web side is responsible for:

```text
Browser
   ↓
FastAPI
   ├── REST API
   ├── WebSocket
   ├── SQLite database (development)
   └── Command/telemetry service boundary
```

The current version includes a simulator so the website can be tested before the real gateway is connected.

## Run on Windows

### 1. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r backend\requirements.txt
```

### 3. Start the server

From the project root:

```powershell
uvicorn backend.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Current behavior

- Temperature, humidity and light values are simulated.
- Fan and LED can be switched from the web interface.
- AUTO/MANUAL mode is displayed and stored.
- The dashboard receives live updates through WebSocket.
- Telemetry is stored in SQLite.
- The command bus is currently a mock implementation.

## Future hardware integration

The real Gateway will replace the simulator and command-bus mock.

The intended architecture is:

```text
Browser
   ↓ HTTPS / WebSocket
Cloud FastAPI
   ↓ command bus
MQTT Broker
   ↓
Windows Gateway
   ↓ USB-RS485
Modbus RTU
   ├── SHT30
   ├── DFRobot SEN0644
   └── Relay 2CH
```

The web project should never import `serial`, `pymodbus`, or hardware-specific modules.


## Access from another phone/laptop on the same Wi-Fi/LAN

The server must listen on all network interfaces.

Recommended startup:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Or double-click:

```text
run_web.bat
```

On the Windows laptop, find its IPv4 address:

```powershell
ipconfig
```

Look for something like:

```text
IPv4 Address . . . . . . . . . . : 192.168.1.25
```

From another device connected to the same network, open:

```text
http://192.168.1.25:8000
```

Do **not** use:

```text
http://127.0.0.1:8000
```

on the other device. `127.0.0.1` always means "this device".

### Windows Firewall

If another device still cannot connect, allow TCP port 8000 through Windows Firewall.

Run PowerShell as Administrator:

```powershell
New-NetFirewallRule -DisplayName "Smart Greenhouse Web 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

Both devices must be on a network where device-to-device communication is allowed. Some public/guest Wi-Fi networks intentionally block clients from seeing each other.

## Chart behavior

The history chart now has:

- A fixed chart area, so it does not keep expanding with incoming data.
- Responsive width for phones/laptops.
- Automatic Y-axis scaling based on the visible data.
- A maximum of 360 displayed points, so long histories do not make the chart unstable or unreadable.
- No chart animation during realtime refresh, preventing visual "drifting".
- Automatic X-axis label skipping.


## Hardware integration

The Windows Gateway is in `gateway/`. It connects to the web backend over `/ws/gateway` and controls the RS485 devices locally. When a web button is clicked, the gateway prints the hardware control log on the laptop and writes it to `gateway/gateway.log`.

For local testing set `WEB_WS_URL=ws://127.0.0.1:8000/ws/gateway`. For a public HTTPS server use `wss://your-domain.com/ws/gateway`. The same `GATEWAY_TOKEN` must be configured on both sides.
