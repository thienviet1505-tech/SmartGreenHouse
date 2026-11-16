// ============================================================
// GreenhouseModel — pure JS physics simulation for a greenhouse
// No DOM, no Three.js — just math.
// ============================================================

const GLAZING = {
  glass: 0.85,
  polycarbonate: 0.75,
  pe_film: 0.88,
};

// Air properties at ~25 °C, 1 atm
const RHO_AIR = 1.2;    // kg/m³  density
const CP_AIR  = 1005;    // J/(kg·K)  specific heat

// Transpiration rate per m² of floor area (kg/s) — simplified constant
const TRANSPIRATION_RATE = 0.0001;

// Molecular weight ratio water / dry-air (used for humidity conversion)
const EPSILON = 0.622;

// Standard atmospheric pressure (Pa)
const P_ATM = 101325;

/**
 * Magnus formula — saturation vapour pressure (Pa) at temperature T (°C).
 */
function saturationVaporPressure(T) {
  return 610.78 * Math.exp((17.27 * T) / (T + 237.3));
}

/**
 * Convert %RH + temperature → absolute humidity (kg water / kg dry-air).
 */
function rhToAbsoluteHumidity(rh, T) {
  const esat = saturationVaporPressure(T);
  const e = (rh / 100) * esat;
  return EPSILON * e / (P_ATM - e);
}

/**
 * Convert absolute humidity (kg/kg) + temperature → %RH.
 */
function absoluteHumidityToRH(w, T) {
  const esat = saturationVaporPressure(T);
  const e = (w * P_ATM) / (EPSILON + w);
  return (e / esat) * 100;
}

export class GreenhouseModel {
  /**
   * @param {Object} opts — all parameters have sensible defaults
   */
  constructor(opts = {}) {
    // ---- Greenhouse geometry (metres) ----
    this.length = opts.length ?? 4.0;
    this.width  = opts.width  ?? 2.5;
    this.height = opts.height ?? 1.8;

    // ---- Glazing ----
    this.glazingType    = opts.glazing ?? 'glass';
    this.transmissivity = GLAZING[this.glazingType] ?? 0.85;

    // ---- Fan ----
    this.fanFlow = opts.fanFlow ?? 0.2;   // m³/s
    this.fanWall = opts.fanWall ?? 'back';

    // ---- LED ----
    this.ledPower    = opts.ledPower    ?? 300;  // W
    this.ledEfficacy = opts.ledEfficacy ?? 100;  // lm/W

    // ---- Thermal ----
    this.uValue      = opts.uValue      ?? 5.5;   // W/(m²·K)
    this.thermalMass  = opts.thermalMass ?? 5000;  // J/K

    // ---- Outside conditions (mutable at runtime) ----
    this.tempOutside = opts.tempOutside ?? 30;   // °C
    this.rhOutside   = opts.rhOutside   ?? 50;   // %
    this.maxSolar    = opts.maxSolar    ?? 600;  // W/m²
    this.cloudCover  = opts.cloudCover  ?? 0.8;  // 0-1

    // ---- Control thresholds ----
    this.fanOnTemp  = opts.fanOnTemp  ?? 30;
    this.fanOffTemp = opts.fanOffTemp ?? 27;
    this.ledOnLux   = opts.ledOnLux   ?? 3000;
    this.ledOffLux  = opts.ledOffLux  ?? 5000;

    // ---- Derived geometry ----
    this._computeGeometry();

    // ---- State ----
    this.temperature = this.tempOutside;
    this.humidity    = this.rhOutside;
    this.light       = 0;
    this.fanOn       = false;
    this.ledOn       = false;
    this.fanMode     = 'AUTO';
    this.ledMode     = 'AUTO';
    this.simTime     = 6 * 3600; // seconds since midnight — start at 06:00
  }

  // ------------------------------------------------------------------
  // Derived geometry helpers
  // ------------------------------------------------------------------

  _computeGeometry() {
    this.roofArea = this.length * this.width;
    this.floorArea = this.roofArea;
    // Total envelope area: 4 walls + roof (no floor)
    this.totalSurfaceArea =
      2 * (this.length * this.height) +
      2 * (this.width  * this.height) +
      this.roofArea;
    // Volume (used for humidity mass balance)
    this.volume = this.length * this.width * this.height;
  }

  // ------------------------------------------------------------------
  // Getters
  // ------------------------------------------------------------------

  /** Current simulation hour (float, e.g. 14.5 = 14:30). */
  get simHour() {
    return this.simTime / 3600;
  }

  // ------------------------------------------------------------------
  // Solar irradiance
  // ------------------------------------------------------------------

  /**
   * Compute instantaneous solar irradiance (W/m²) on the roof.
   * Bell-curve peaking at 12:00; zero before 05:00 and after 19:00.
   */
  _solarIrradiance(hour) {
    if (hour < 5 || hour > 19) return 0;
    const cosVal = Math.cos(Math.PI * (hour - 12) / 7);
    return this.maxSolar * (1 - this.cloudCover) * Math.max(0, cosVal);
  }

  // ------------------------------------------------------------------
  // Main simulation step
  // ------------------------------------------------------------------

  /**
   * Advance the simulation by `dt` real seconds.
   * Internally uses fixed 1-second sub-steps for stability.
   */
  step(dt) {
    const dtSub = 1; // 1 simulated second per sub-step
    const nSteps = Math.round(dt);

    for (let i = 0; i < nSteps; i++) {
      this._substep(dtSub);
    }
  }

  /**
   * Single 1-second physics sub-step.
   */
  _substep(dtSub) {
    const hour = this.simTime / 3600;

    // ---- Solar ----
    const Qsolar = this._solarIrradiance(hour);

    // ---- Light (lux) ----
    const solarLux = Qsolar * 120 * this.transmissivity;
    const ledLux   = this.ledOn ? (this.ledPower * this.ledEfficacy) / this.floorArea : 0;
    this.light = solarLux + ledLux;

    // ---- Auto-control logic (before heat balance so actuator states are current) ----
    this._autoControl();

    // ---- Heat balance ----
    const Qin =
      Qsolar * this.roofArea * this.transmissivity +   // solar gain through roof
      (this.ledOn ? this.ledPower : 0);                 // LED waste heat

    const UA = this.uValue * this.totalSurfaceArea;
    const fanHeatLoss = this.fanOn
      ? this.fanFlow * RHO_AIR * CP_AIR
      : 0;

    // dT = [Qin - (UA + fanLoss) * (T - Tout)] * dt / C
    const dT =
      (Qin - (UA + fanHeatLoss) * (this.temperature - this.tempOutside)) *
      dtSub / this.thermalMass;

    this.temperature += dT;

    // ---- Humidity ----
    this._updateHumidity(dtSub);

    // ---- Advance clock (wrap at 24 h) ----
    this.simTime = (this.simTime + dtSub) % (24 * 3600);
  }

  // ------------------------------------------------------------------
  // Humidity sub-model
  // ------------------------------------------------------------------

  _updateHumidity(dtSub) {
    // Current absolute humidity inside (kg water / kg dry-air)
    let wInside = rhToAbsoluteHumidity(this.humidity, this.temperature);

    // Mass of dry air inside (kg)
    const mAir = RHO_AIR * this.volume;

    // Transpiration adds moisture (kg/s)
    const transpirationMass = TRANSPIRATION_RATE * this.floorArea; // kg/s

    // Change in absolute humidity from transpiration
    const dwTranspiration = (transpirationMass / mAir) * dtSub;
    wInside += dwTranspiration;

    // Fan ventilation mixes inside air with outside air
    if (this.fanOn) {
      const wOutside = rhToAbsoluteHumidity(this.rhOutside, this.tempOutside);
      // Fraction of air exchanged per sub-step
      const exchangeRate = (this.fanFlow * dtSub) / this.volume;
      wInside += (wOutside - wInside) * Math.min(exchangeRate, 1);
    }

    // Convert back to %RH at current inside temperature
    let rh = absoluteHumidityToRH(wInside, this.temperature);

    // Clamp
    rh = Math.max(20, Math.min(99, rh));
    this.humidity = rh;
  }

  // ------------------------------------------------------------------
  // Auto-control
  // ------------------------------------------------------------------

  _autoControl() {
    // Fan hysteresis
    if (this.fanMode === 'AUTO') {
      if (this.temperature >= this.fanOnTemp)  this.fanOn = true;
      if (this.temperature <= this.fanOffTemp) this.fanOn = false;
    }

    // LED hysteresis
    if (this.ledMode === 'AUTO') {
      if (this.light <= this.ledOnLux)  this.ledOn = true;
      if (this.light >= this.ledOffLux) this.ledOn = false;
    }
  }

  // ------------------------------------------------------------------
  // Manual overrides
  // ------------------------------------------------------------------

  /** Force fan ON or OFF (switches to MANUAL mode). */
  setManualFan(on) {
    this.fanMode = 'MANUAL';
    this.fanOn = !!on;
  }

  /** Force LED ON or OFF (switches to MANUAL mode). */
  setManualLed(on) {
    this.ledMode = 'MANUAL';
    this.ledOn = !!on;
  }

  /** Return fan control to AUTO. */
  setAutoFan() {
    this.fanMode = 'AUTO';
  }

  /** Return LED control to AUTO. */
  setAutoLed() {
    this.ledMode = 'AUTO';
  }

  // ------------------------------------------------------------------
  // Reset
  // ------------------------------------------------------------------

  /** Reset all state to initial conditions. */
  reset() {
    this.temperature = this.tempOutside;
    this.humidity    = this.rhOutside;
    this.light       = 0;
    this.fanOn       = false;
    this.ledOn       = false;
    this.fanMode     = 'AUTO';
    this.ledMode     = 'AUTO';
    this.simTime     = 6 * 3600;
  }
}
