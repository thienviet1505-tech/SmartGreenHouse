import asyncio
import math
import random
from datetime import datetime, timezone

from sqlalchemy import select

from ..database import SessionLocal
from ..models import ActuatorState, ControlRule, GatewayStatus, SensorReading


class GreenhouseSimulator:
    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self.temperature = 28.0
        self.humidity = 72.0
        self.light = 4200.0

    def _get_or_create_actuators(self, db):
        item = db.scalar(select(ActuatorState).order_by(ActuatorState.id.desc()))
        if item is None:
            item = ActuatorState()
            db.add(item)
            db.flush()
        return item

    def _get_or_create_rules(self, db):
        item = db.scalar(select(ControlRule).order_by(ControlRule.id.desc()))
        if item is None:
            item = ControlRule()
            db.add(item)
            db.flush()
        return item

    def _tick(self):
        phase = datetime.now(timezone.utc).timestamp() / 180.0
        self.temperature = 28.0 + math.sin(phase) * 3.0 + random.uniform(-0.2, 0.2)
        self.humidity = 72.0 - (self.temperature - 28.0) * 1.3 + random.uniform(-0.5, 0.5)

        daylight_phase = datetime.now(timezone.utc).hour
        daylight = max(0.0, math.sin((daylight_phase - 6) / 12 * math.pi))
        self.light = 1000 + daylight * 9000 + random.uniform(-120, 120)

    async def run(self):
        while True:
            try:
                self._tick()
                with SessionLocal() as db:
                    actuators = self._get_or_create_actuators(db)
                    rules = self._get_or_create_rules(db)

                    if actuators.fan_mode == "AUTO":
                        if self.temperature >= rules.fan_on_temp:
                            actuators.fan_state = True
                        elif self.temperature <= rules.fan_off_temp:
                            actuators.fan_state = False

                    if actuators.led_mode == "AUTO":
                        if self.light <= rules.led_on_lux:
                            actuators.led_state = True
                        elif self.light >= rules.led_off_lux:
                            actuators.led_state = False

                    db.add(
                        SensorReading(
                            temperature=self.temperature,
                            humidity=self.humidity,
                            light=self.light,
                        )
                    )
                    actuators.timestamp = datetime.now(timezone.utc)

                    status = db.scalar(select(GatewayStatus).order_by(GatewayStatus.id.desc()))
                    if status is None:
                        status = GatewayStatus()
                        db.add(status)
                    status.online = True
                    status.rs485_ok = True
                    status.timestamp = datetime.now(timezone.utc)

                    db.commit()
            except Exception:
                pass

            await asyncio.sleep(self.interval)
