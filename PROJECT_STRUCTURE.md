# Project Structure

```text
smart-greenhouse-web/
├── README.md
├── PROJECT_STRUCTURE.md
├── .env.example
├── run_web.bat
├── run_gateway.bat
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── websocket.py
│       ├── gateway_ws.py
│       ├── api/routes.py
│       └── services/
│           ├── command_bus.py
│           └── simulator.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── gateway/
    ├── README.md
    ├── .env.example
    ├── requirements.txt
    ├── config.py
    ├── logger.py
    ├── gateway.py
    ├── modbus/client.py
    ├── devices/sht30.py
    ├── devices/light.py
    ├── devices/relay.py
    ├── control/controller.py
    └── tools/set_light_id.py
```

## Separation

### Web

The `backend/` + `frontend/` side handles dashboard, database, REST API, browser WebSocket and gateway WebSocket.

### Hardware

The `gateway/` side handles Windows COM port, USB-RS485, Modbus RTU, sensors, relay, local AUTO control and laptop logging.

No browser code directly accesses RS485.

## Runtime communication

```text
Browser
  │ HTTPS/WebSocket
  ▼
FastAPI
  │ WebSocket
  ▼
Windows Gateway
  │ USB-RS485
  ▼
Modbus RTU
  ├── SHT30
  ├── SEN0644
  └── Relay 2CH
```

## Web command logging

```text
Web button
  ▼
FastAPI
  ▼
Gateway WebSocket
  ▼
gateway.py
  ▼
gateway.log + Windows console
```
