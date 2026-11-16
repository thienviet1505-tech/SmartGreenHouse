// ============================================================
// sim.js — Simulation page controller
// Ties GreenhouseModel + GreenhouseScene + UI panel together.
// ============================================================

import { GreenhouseModel } from './model.js';
import { GreenhouseScene } from './scene.js';

const SPEEDS = [1, 2, 5, 10, 30, 60, 120, 300, 600];
const UI_INTERVAL = 200;
const CHART_SIM_INTERVAL = 120;
const CHART_MAX = 200;

let model = null;
let scene = null;
let animId = null;
let playing = false;
let speed = 1;
let prevT = 0;
let lastUI = 0;
let lastChartSim = 0;
let chartBuf = [];
let el = {};
let prevDims = '';  // track dimension changes for rebuild

const $ = id => document.getElementById(id);

function cache() {
  el = {
    canvas:   $('simCanvas'),
    time:     $('simTime'),
    slider:   $('simSpeed'),
    speedLbl: $('simSpeedLabel'),
    play:     $('simPlayBtn'),
    reset:    $('simResetBtn'),
    tDisp:    $('simTempDisplay'),
    hDisp:    $('simHumDisplay'),
    lDisp:    $('simLuxDisplay'),
    fanSt:    $('simFanStatus'),
    ledSt:    $('simLedStatus'),
    chart:    $('simChart'),
    // params
    length: $('simLength'),  width: $('simWidth'),  height: $('simHeight'),
    glazing: $('simGlazing'),
    fanFlow: $('simFanFlow'), ledPow: $('simLedPower'),
    tOut: $('simTempOut'), rhOut: $('simRhOut'),
    solar: $('simMaxSolar'), cloud: $('simCloud'),
    fOn: $('simFanOnTemp'), fOff: $('simFanOffTemp'),
    lOn: $('simLedOnLux'),  lOff: $('simLedOffLux'),
    // control buttons
    fanAuto: $('simFanAuto'),   fanMan: $('simFanManual'),
    ledAuto: $('simLedAuto'),   ledMan: $('simLedManual'),
    fanSw: $('simFanSwitch'),   ledSw: $('simLedSwitch'),
    cloudVal: $('simCloudVal'),
  };
}

/* ---- read a number from input (handles 0 correctly) ---- */
function n(e, d) {
  if (!e) return d;
  const v = parseFloat(e.value);
  return Number.isFinite(v) ? v : d;
}

/* ---- current dimension key for detecting changes ---- */
function dimKey() {
  return `${n(el.length,4)}_${n(el.width,2.5)}_${n(el.height,1.8)}_${el.glazing?.value||'glass'}`;
}

/* ---- sync UI inputs → model, rebuild scene if dims changed ---- */
function sync() {
  if (!model) return;
  model.length      = n(el.length, 4);
  model.width       = n(el.width, 2.5);
  model.height      = n(el.height, 1.8);
  if (el.glazing) {
    model.glazingType = el.glazing.value;
    const G = { glass: 0.85, polycarbonate: 0.75, pe_film: 0.88 };
    model.transmissivity = G[model.glazingType] || 0.85;
  }
  model.fanFlow     = n(el.fanFlow, 0.2);
  model.ledPower    = n(el.ledPow, 300);
  model.tempOutside = n(el.tOut, 30);
  model.rhOutside   = n(el.rhOut, 50);
  model.maxSolar    = n(el.solar, 600);
  model.cloudCover  = n(el.cloud, 80) / 100;
  model.fanOnTemp   = n(el.fOn, 30);
  model.fanOffTemp  = n(el.fOff, 27);
  model.ledOnLux    = n(el.lOn, 3000);
  model.ledOffLux   = n(el.lOff, 5000);
  model._computeGeometry();

  if (el.cloudVal) el.cloudVal.textContent = Math.round(model.cloudCover * 100) + '%';

  // Rebuild 3D scene if dimensions or glazing changed
  const dk = dimKey();
  if (dk !== prevDims && scene) {
    scene.rebuild();
    prevDims = dk;
  }
}

/* ---- format sim time ---- */
function fmtTime(s) {
  const days = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const hm = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  return days > 0 ? `Ngày ${days + 1} — ${hm}` : hm;
}

/* ---- update on-screen values ---- */
function updateUI(now) {
  if (now - lastUI < UI_INTERVAL) return;
  lastUI = now;
  if (!model) return;

  if (el.time) el.time.textContent = fmtTime(model.simTime);
  if (el.tDisp) el.tDisp.textContent = model.temperature.toFixed(1) + '°C';
  if (el.hDisp) el.hDisp.textContent = model.humidity.toFixed(0) + '%';
  if (el.lDisp) el.lDisp.textContent = Math.round(model.light).toLocaleString('vi-VN') + ' lux';

  if (el.fanSt) {
    const on = model.fanOn, mode = model.fanMode === 'AUTO' ? 'Tự động' : 'Thủ công';
    el.fanSt.textContent = `🌀 ${on ? 'BẬT' : 'TẮT'} (${mode})`;
    el.fanSt.className = 'sim-rd sim-status ' + (on ? 'on' : 'off');
  }
  if (el.ledSt) {
    const on = model.ledOn, mode = model.ledMode === 'AUTO' ? 'Tự động' : 'Thủ công';
    el.ledSt.textContent = `💡 ${on ? 'BẬT' : 'TẮT'} (${mode})`;
    el.ledSt.className = 'sim-rd sim-status ' + (on ? 'on' : 'off');
  }

  if (el.fanSw) { el.fanSw.checked = model.fanOn; el.fanSw.disabled = model.fanMode === 'AUTO'; }
  if (el.ledSw) { el.ledSw.checked = model.ledOn; el.ledSw.disabled = model.ledMode === 'AUTO'; }

  const setAct = (a, b, isA) => {
    if (a) a.classList.toggle('active', isA);
    if (b) b.classList.toggle('active', !isA);
  };
  setAct(el.fanAuto, el.fanMan, model.fanMode === 'AUTO');
  setAct(el.ledAuto, el.ledMan, model.ledMode === 'AUTO');
}

/* ---- chart ---- */
function recordChart() {
  if (model.simTime - lastChartSim < CHART_SIM_INTERVAL) return;
  lastChartSim = model.simTime;
  chartBuf.push({ t: model.simTime, temp: model.temperature, hum: model.humidity, lux: model.light });
  if (chartBuf.length > CHART_MAX) chartBuf.shift();
  drawChart();
}

function drawChart() {
  const cv = el.chart;
  if (!cv || chartBuf.length < 2) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = cv.getBoundingClientRect();
  if (!rect.width) return;
  cv.width = Math.round(rect.width * dpr);
  cv.height = Math.round(rect.height * dpr);
  const c = cv.getContext('2d');
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = rect.width, H = rect.height, P = 6;

  function line(vals, color, lo, hi) {
    const r = hi - lo || 1;
    c.beginPath(); c.strokeStyle = color; c.lineWidth = 1.8; c.lineJoin = 'round';
    for (let i = 0; i < vals.length; i++) {
      const x = P + (i / (vals.length - 1)) * (W - P * 2);
      const y = P + (H - P * 2) - ((vals[i] - lo) / r) * (H - P * 2);
      i === 0 ? c.moveTo(x, y) : c.lineTo(x, y);
    }
    c.stroke();
  }

  const temps = chartBuf.map(p => p.temp);
  const hums = chartBuf.map(p => p.hum);
  const tLo = Math.min(...temps) - 2, tHi = Math.max(...temps) + 2;
  const hLo = Math.min(...hums) - 5, hHi = Math.max(...hums) + 5;

  line(temps, '#e5533d', tLo, tHi);
  line(hums, '#2b8bd6', hLo, hHi);

  c.font = '10px system-ui, sans-serif';
  c.fillStyle = '#e5533d'; c.fillText('🌡️ Nhiệt độ', P, 12);
  c.fillStyle = '#2b8bd6'; c.fillText('💧 Độ ẩm', P + 90, 12);
}

/* ---- animation loop ---- */
function loop(ts) {
  animId = requestAnimationFrame(loop);
  if (!prevT) { prevT = ts; return; }
  const dt = Math.min((ts - prevT) / 1000, 0.1);
  prevT = ts;

  if (playing && model) {
    model.step(dt * speed);
    recordChart();
  }
  if (scene) scene.update();
  updateUI(ts);
}

/* ---- bind events ---- */
function bind() {
  // Dimension inputs (trigger rebuild)
  const dimInputs = [el.length, el.width, el.height, el.glazing];
  for (const e of dimInputs) {
    if (!e) continue;
    e.addEventListener('change', sync);
  }

  // Other parameter inputs (no rebuild needed)
  const otherInputs = [el.fanFlow, el.ledPow, el.tOut, el.rhOut, el.solar,
    el.cloud, el.fOn, el.fOff, el.lOn, el.lOff];
  for (const e of otherInputs) {
    if (!e) continue;
    e.addEventListener('input', sync);
    e.addEventListener('change', sync);
  }

  // Speed
  if (el.slider) {
    el.slider.min = 0; el.slider.max = SPEEDS.length - 1;
    el.slider.value = 0; el.slider.step = 1;
    if (el.speedLbl) el.speedLbl.textContent = '1×';
    el.slider.addEventListener('input', () => {
      speed = SPEEDS[+el.slider.value];
      if (el.speedLbl) el.speedLbl.textContent = speed + '×';
    });
  }

  // Play / Pause
  if (el.play) el.play.addEventListener('click', () => {
    playing = !playing;
    el.play.textContent = playing ? '⏸ Dừng' : '▶ Chạy';
    el.play.title = playing ? 'Tạm dừng mô phỏng' : 'Chạy mô phỏng';
    if (playing) prevT = 0;
  });

  // Reset
  if (el.reset) el.reset.addEventListener('click', () => {
    playing = false;
    if (el.play) { el.play.textContent = '▶ Chạy'; el.play.title = 'Chạy mô phỏng'; }
    if (model) model.reset();
    prevT = 0; lastChartSim = 0; chartBuf = [];
    drawChart();
    updateUI(performance.now());
  });

  // Fan mode
  if (el.fanAuto) el.fanAuto.addEventListener('click', () => { if (model) model.setAutoFan(); });
  if (el.fanMan) el.fanMan.addEventListener('click', () => { if (model) model.setManualFan(model.fanOn); });
  if (el.ledAuto) el.ledAuto.addEventListener('click', () => { if (model) model.setAutoLed(); });
  if (el.ledMan) el.ledMan.addEventListener('click', () => { if (model) model.setManualLed(model.ledOn); });

  // Manual switches
  if (el.fanSw) el.fanSw.addEventListener('change', () => {
    if (model && model.fanMode === 'MANUAL') model.fanOn = el.fanSw.checked;
  });
  if (el.ledSw) el.ledSw.addEventListener('change', () => {
    if (model && model.ledMode === 'MANUAL') model.ledOn = el.ledSw.checked;
  });
}

/* ---- public API ---- */
export function initSimulation() {
  cache();
  if (!el.canvas) { console.warn('[Sim] #simCanvas not found'); return; }

  model = new GreenhouseModel();
  sync();
  prevDims = dimKey();
  scene = new GreenhouseScene(el.canvas, model);

  playing = false; speed = 1; prevT = 0; lastUI = 0;
  lastChartSim = 0; chartBuf = [];

  bind();
  if (el.play) { el.play.textContent = '▶ Chạy'; el.play.title = 'Chạy mô phỏng'; }
  updateUI(performance.now());
  animId = requestAnimationFrame(loop);
}

export function disposeSimulation() {
  if (animId) { cancelAnimationFrame(animId); animId = null; }
  playing = false; prevT = 0;
  if (scene) { scene.dispose(); scene = null; }
  model = null; chartBuf = [];
}
