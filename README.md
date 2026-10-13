# Smart Greenhouse

Web dashboard (FastAPI) + Windows hardware gateway (USB-RS485 / Modbus RTU) for a small greenhouse:
1 light sensor (DFRobot SEN0644), 1 temperature/humidity sensor (TH10S-B-PE, SHT30) and a 2-channel relay
(fan + LED). The web side contains no serial code; only `gateway/` talks to RS485.

```text
Browser --HTTPS/WebSocket--> FastAPI --WebSocket--> Windows Gateway --USB-RS485--> Modbus RTU devices
```

## Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install -r gateway\requirements.txt
copy .env.example .env             # set GATEWAY_TOKEN and DASHBOARD_TOKEN
copy gateway\.env.example gateway\.env
```

1. `run_web.bat` - web server on port 8000 (reads the root `.env`).
2. `run_gateway.bat` - hardware gateway (reads `gateway\.env`). Set the Modbus addresses first:
   see `gateway\README.md`.

Open `http://127.0.0.1:8000`. API docs: `/docs`.

`SIMULATOR_ENABLED=true` in `.env` runs the built-in simulator instead of real hardware.

## Security (read before exposing the site to the internet)

* Set `DASHBOARD_TOKEN` in `.env`. Without it anyone who can reach the server can switch the fan/LED.
  The browser asks for the token once and keeps it in `localStorage`.
* Set a real `GATEWAY_TOKEN` (the same value in `.env` and `gateway\.env`).
* Use HTTPS (reverse proxy / tunnel) so the tokens are not sent in clear text.
* The server logs a warning at start-up if either token is still the default/empty.

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

The Windows Gateway (`gateway/`) connects to the web backend over `/ws/gateway` and controls the RS485
devices locally. Web buttons are logged on the laptop and in `gateway/gateway.log`.
`WEB_WS_URL=ws://127.0.0.1:8000/ws/gateway` for local tests, `wss://your-domain.com/ws/gateway` for a public server.
