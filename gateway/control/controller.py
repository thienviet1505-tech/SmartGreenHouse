from dataclasses import dataclass


@dataclass
class ControlRules:
    fan_on_temp: float = 30.0
    fan_off_temp: float = 27.0
    led_on_lux: float = 3000.0
    led_off_lux: float = 5000.0


class AutoController:
    def __init__(self, rules):
        self.rules = rules
        self.fan_mode = "AUTO"
        self.led_mode = "AUTO"

    def update_rules(self, rules):
        self.rules = rules

    def evaluate(self, temperature, light, fan_state, led_state):
        """temperature/light may be None (sensor missing or stale): the
        matching output then simply keeps its current state."""
        next_fan, next_led = fan_state, led_state
        if self.fan_mode == "AUTO" and temperature is not None:
            if temperature >= self.rules.fan_on_temp:
                next_fan = True
            elif temperature <= self.rules.fan_off_temp:
                next_fan = False
        if self.led_mode == "AUTO" and light is not None:
            if light <= self.rules.led_on_lux:
                next_led = True
            elif light >= self.rules.led_off_lux:
                next_led = False
        return next_fan, next_led
