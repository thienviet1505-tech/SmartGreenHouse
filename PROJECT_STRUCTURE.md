# Project Structure

```text
smart-greenhouse-web/
│
├── README.md
├── PROJECT_STRUCTURE.md
├── run_web.bat
│
├── backend/
│   ├── requirements.txt
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── command_bus.py
│       │   └── simulator.py
│       │
│       └── websocket.py
│
└── frontend/
    ├── index.html
    ├── app.js
    └── style.css
```

## 1. `frontend/`

Only the user interface.

### `index.html`

Main dashboard:

- Temperature
- Humidity
- Light
- Fan
- LED
- AUTO/MANUAL
- Gateway status
- History chart

### `app.js`

Frontend logic:

- Calls REST API.
- Opens WebSocket.
- Updates live values.
- Sends fan/LED commands.
- Draws the history chart.

### `style.css`

Dashboard layout and responsive styling.

---

## 2. `backend/app/main.py`

FastAPI application entry point.

Responsibilities:

- Create the FastAPI app.
- Serve frontend files.
- Register API routes.
- Start the simulator.
- Expose WebSocket endpoint.

---

## 3. `backend/app/config.py`

Central configuration.

Examples:

```text
DATABASE_URL
SIMULATOR_ENABLED
SIMULATOR_INTERVAL
```

Later this file will also contain:

```text
MQTT_BROKER
MQTT_PORT
MQTT_USERNAME
MQTT_PASSWORD
```

---

## 4. `backend/app/database.py`

Database connection and SQLAlchemy session.

Development uses SQLite:

```text
smart_greenhouse.db
```

For public deployment, this can later be changed to PostgreSQL without changing the frontend.

---

## 5. `backend/app/models.py`

Database models.

Main models:

```text
SensorReading
ActuatorState
ControlRule
CommandLog
GatewayStatus
```

---

## 6. `backend/app/schemas.py`

Pydantic models for API input/output.

Examples:

```text
ControlCommand
TelemetryPayload
ControlRules
DashboardState
```

Keeping schemas separate makes the API contract clear.

---

## 7. `backend/app/api/routes.py`

REST API.

Current endpoints:

```text
GET  /api/state
GET  /api/history
GET  /api/status

POST /api/control/fan
POST /api/control/led

PUT  /api/rules
```

Future gateway endpoints can be added here:

```text
POST /api/ingest/telemetry
POST /api/ingest/event
```

---

## 8. `backend/app/services/command_bus.py`

Abstraction between the web backend and the physical gateway.

Current implementation:

```text
MockCommandBus
```

It does not access hardware.

Later:

```text
MqttCommandBus
```

will publish commands to the MQTT broker.

The rest of the backend should not need to know whether the command is delivered by MQTT or another transport.

---

## 9. `backend/app/services/simulator.py`

Development-only simulated greenhouse.

It generates:

```text
Temperature
Humidity
Light
```

and applies web commands to simulated relay states.

When the real Gateway is connected, this service will be disabled:

```text
SIMULATOR_ENABLED=false
```

---

## 10. `backend/app/websocket.py`

Realtime communication.

The backend broadcasts:

```text
temperature
humidity
light
fan
led
fan_mode
led_mode
gateway_online
timestamp
```

to all connected browsers.

---

# Data ownership

## Web/Cloud owns

```text
Users
Dashboard state
History storage
Web settings
Remote commands
Command logs
Realtime browser updates
```

## Gateway owns

```text
RS485
Modbus RTU
Sensor polling
Relay communication
Local AUTO control
Local safety behavior
Local buffering when Internet is unavailable
```

This separation is intentional.

The web server must not contain:

```text
serial.Serial(...)
pymodbus
COM3
RS485 A/B
Modbus register polling
```

Those belong to the Gateway project.


## Network access

Use `run_web.bat` or:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Then other devices on the same LAN can use:

```text
http://<LAPTOP-IP>:8000
```

The browser connects back to the same host for REST and WebSocket, so no hard-coded `localhost` is used in the frontend.
