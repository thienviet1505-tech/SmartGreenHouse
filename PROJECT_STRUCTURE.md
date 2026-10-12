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
<<<<<<< HEAD
│       ├── api/routes.py
│       └── services/
│           ├── command_bus.py
=======
│       ├── security.py
│       ├── timeutil.py
│       ├── api/routes.py
│       └── services/
│           ├── command_bus.py
│           ├── state.py
>>>>>>> Rac
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
<<<<<<< HEAD
    └── tools/set_light_id.py
=======
    └── tools/
        ├── probe_modbus.py
        ├── set_light_id.py
        └── set_relay_id.py
>>>>>>> Rac
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
<<<<<<< HEAD
  ├── SHT30
  ├── SEN0644
  └── Relay 2CH
=======
  ├── TH10S-B-PE (SHT30)  id 1
  ├── SEN0644             id 2
  └── Relay 2CH           id 3
>>>>>>> Rac
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
