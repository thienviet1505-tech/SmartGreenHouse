"use strict";
const $ = (id) => document.getElementById(id);
const has = (v) => v !== null && v !== undefined;
const num = (v, d = 1) => (has(v) ? Number(v).toFixed(d) : "--");
const pad = (n) => String(n).padStart(2, "0");
const hm = (t) => { const d = new Date(t); return pad(d.getHours()) + ":" + pad(d.getMinutes()); };
const ymd = (t) => { const d = new Date(t); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const store = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k)); localStorage.setItem(k, JSON.stringify(v)); } catch { return null; } };
const TOKEN_KEY = "greenhouse_access_token";
const SENS = {
  temperature: { name: "Nhiệt độ", unit: "°C", d: 1, color: "--heat", icon: "🌡️" },
  humidity: { name: "Độ ẩm", unit: "%", d: 0, color: "--water", icon: "💧" },
  light: { name: "Ánh sáng", unit: "lux", d: 0, color: "--sun", icon: "☀️" },
};
const DEV = { fan: { name: "Quạt", icon: "🌀" }, led: { name: "Đèn LED", icon: "💡" } };
const SAFE0 = { temperature: [18, 32], humidity: [50, 85], light: [2000, 60000] };
const SAFE_IDS = { temperature: ["sfT0", "sfT1"], humidity: ["sfH0", "sfH1"], light: ["sfL0", "sfL1"] };
const RULE_IDS = { fan_on_temp: "fanOnTemp", fan_off_temp: "fanOffTemp", led_on_lux: "ledOnLux", led_off_lux: "ledOffLux" };
const LV = { low: "Thấp", high: "Cao", ok: "Ổn định" };
const ICON = { warn: "⚠️", ok: "✅", info: "ℹ️" };
const PAGES = ["overview", "control", "monitor", "history", "alerts", "settings", "simulation"];
const INFO = {
  overview: ["Tổng quan", "Nhà kính thông minh. Dữ liệu cảm biến theo thời gian thực"],
  control: ["Điều khiển", "Cài đặt và điều khiển các thiết bị trong nhà kính"],
  monitor: ["Giám sát", "Tình trạng cảm biến, kết nối và xu hướng gần đây"],
  history: ["Lịch sử dữ liệu", "Biểu đồ và dữ liệu môi trường theo thời gian"],
  alerts: ["Thông báo", "Sự kiện và cảnh báo từ hệ thống"],
  settings: ["Cài đặt", "Ngưỡng tự động, vùng an toàn và giao diện"],
  simulation: ["Mô phỏng 3D", "Mô phỏng nhà kính với mô hình vật lý. Kết quả mang tính minh họa"],
};

let ws, state = null, rules = null, events = store("gh_events") || [], alertTab = "all";
let hKey = "temperature", hDate = ymd(Date.now()), hPts = [], hSpan = 1440, hover = null, hView = null, spk = null;
let tokenPrompt = null, authBlocked = false, wsStopped = false, toastTimer;
const pending = {}, intent = {}, prev = {}, since = {}, announce = {}, prevDev = {};
let prevG, prevB;

const safe = () => ({ ...SAFE0, ...(store("gh_safe") || {}) });
const level = (k, v) => { if (!has(v)) return null; const [lo, hi] = safe()[k]; return v < lo ? "low" : v > hi ? "high" : "ok"; };
const when = (t) => (new Date(t).toDateString() === new Date().toDateString() ? "" : `${pad(new Date(t).getDate())}/${pad(new Date(t).getMonth() + 1)} `) + hm(t);

/* ---------- thông báo nhanh và nhật ký sự kiện ---------- */
function toast(msg, bad = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = "toast"), 3500);
}
function addEvent(type, title, detail = "") {
  events = [{ t: Date.now(), type, title, detail }, ...events].slice(0, 100);
  store("gh_events", events);
  renderAlerts();
  renderBadge();
  if (type === "warn") toast(title, true);
}
function renderBadge() {
  const seen = store("gh_seen") || 0, n = events.filter((e) => e.t > seen).length;
  $("badge").hidden = !n || location.hash === "#alerts";
  $("badge").textContent = n > 9 ? "9+" : n;
}
function renderAlerts() {
  const ul = $("alertList");
  ul.textContent = "";
  const rows = events.filter((e) => alertTab === "all" || e.type === alertTab);
  if (!rows.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "Chưa có thông báo. Hệ thống ghi lại khi số đo vượt khỏi hoặc trở về vùng an toàn.";
    ul.append(li);
    return;
  }
  for (const e of rows) {
    const li = document.createElement("li");
    li.className = e.type;
    li.innerHTML = '<span class="ic"></span><div><b></b><p></p></div><time></time>';
    li.querySelector(".ic").textContent = ICON[e.type];
    li.querySelector("b").textContent = e.title;
    li.querySelector("p").textContent = e.detail;
    li.querySelector("time").textContent = when(e.t);
    ul.append(li);
  }
}

/* ---------- mã truy cập (giữ nguyên logic) ---------- */
const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
function askToken(message) {
  const dlg = $("tokenDlg");
  $("tokenMsg").textContent = message;
  $("tokenInput").value = "";
  return new Promise((resolve) => {
    dlg.addEventListener("close", () => {
      const v = dlg.returnValue === "ok" ? $("tokenInput").value.trim() : "";
      if (v) localStorage.setItem(TOKEN_KEY, v);
      resolve(v);
    }, { once: true });
    dlg.returnValue = "";
    dlg.showModal();
  });
}
function ensureToken(message = "Nhập mã truy cập để xem và điều khiển nhà kính.") {
  if (!tokenPrompt) {
    tokenPrompt = askToken(message)
      .then((value) => { authBlocked = !value; if (value && wsStopped) { wsStopped = false; connectWebSocket(); } return value; })
      .finally(() => { tokenPrompt = null; });
  }
  return tokenPrompt;
}
async function fetchJson(url, options = {}, retry = true) {
  const sent = getToken();
  const res = await fetch(url, { ...options, headers: { "Content-Type": "application/json", ...(sent ? { Authorization: `Bearer ${sent}` } : {}), ...(options.headers || {}) } });
  if (res.status === 401 && retry) {
    if (getToken() === sent) localStorage.removeItem(TOKEN_KEY);
    const token = getToken() || (await ensureToken());
    if (token && token !== sent) return fetchJson(url, options, false);
    authBlocked = true;
  }
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || `HTTP ${res.status}`); }
  return res.json();
}

/* ---------- theo dõi số đo và sinh thông báo ---------- */
function watch(s) {
  const now = Date.now();
  for (const k in SENS) {
    const lv = level(k, s[k]);
    if (!lv) continue;
    const S = SENS[k], [lo, hi] = safe()[k];
    if (prev[k] !== undefined && lv !== prev[k]) {
      since[k] = now;
      if (lv !== "ok") {
        announce[k] = true;
        addEvent("warn", `${S.name} ${lv === "high" ? "cao" : "thấp"} hơn vùng an toàn`, `${num(s[k], S.d)} ${S.unit} (vùng an toàn ${lo} đến ${hi} ${S.unit})`);
      }
    }
    if (lv === "ok" && announce[k] && now - (since[k] || now) >= 60000) {
      announce[k] = false;
      addEvent("ok", `${S.name} đã ổn định`, `${num(s[k], S.d)} ${S.unit}, nằm trong vùng an toàn`);
    }
    prev[k] = lv;
  }
  for (const d in DEV) {
    const on = Boolean(s[d + "_state"]);
    if (prevDev[d] !== undefined && prevDev[d] !== on) addEvent("info", `${DEV[d].name} ${on ? "bật" : "tắt"}`, s[d + "_mode"] === "AUTO" ? "Tự động theo ngưỡng" : "Điều khiển thủ công");
    prevDev[d] = on;
  }
  const g = Boolean(s.gateway_online), b = Boolean(s.rs485_ok);
  if (prevG !== undefined && prevG !== g) addEvent(g ? "ok" : "warn", g ? "Gateway đã kết nối lại" : "Gateway mất kết nối", g ? "" : "Lệnh điều khiển chưa gửi được tới phần cứng");
  if (g && prevB !== undefined && prevB !== b) addEvent(b ? "ok" : "warn", b ? "RS485 đã phục hồi" : "Lỗi RS485", s.last_error || "");
  prevG = g; prevB = b;
}

/* ---------- hiển thị trạng thái ---------- */
function setChip(id, lv) { const c = $(id); c.className = "chip " + (lv || ""); c.textContent = lv ? LV[lv] : ""; }
function autoText(d) {
  if (!rules) return "Tự động theo ngưỡng.";
  return d === "fan" ? `Tự động: bật khi từ ${rules.fan_on_temp}°C, tắt khi xuống ${rules.fan_off_temp}°C.` : `Tự động: bật khi dưới ${rules.led_on_lux} lux, tắt khi lên ${rules.led_off_lux} lux.`;
}
function done(d) { clearTimeout(pending[d]); delete intent[d]; $("dev-" + d).classList.remove("busy"); }
function renderDev(d, on, mode) {
  on = Boolean(on);
  $("dev-" + d).classList.toggle("on", on);
  $("ds-" + d).textContent = on ? "Đang hoạt động" : "Đang tắt";
  $("ds-" + d).className = "st" + (on ? " ok" : "");
  document.querySelectorAll(`#dev-${d} .mode button`).forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  $("sw-" + d).checked = on;
  $("sw-" + d).disabled = mode === "AUTO";
  $("dn-" + d).textContent = mode === "AUTO" ? autoText(d) : "Thủ công: bạn tự bật/tắt. Ngưỡng tự động tạm dừng.";
  $("od-" + d).textContent = `${on ? "Đang chạy" : "Đang tắt"} (${mode === "AUTO" ? "tự động" : "thủ công"})`;
  const i = intent[d];
  if (i && i.mode === mode && (mode === "AUTO" || i.state === on)) done(d);
}
function updateAge() {
  const ts = state && state.timestamp ? Date.parse(state.timestamp) : NaN;
  const s = Number.isFinite(ts) ? Math.max(0, Math.round((Date.now() - ts) / 1000)) : null;
  const el = $("m-age");
  el.textContent = s === null ? "Chưa có dữ liệu" : s < 60 ? `${s} giây trước` : `${Math.round(s / 60)} phút trước`;
  el.className = "st " + (s !== null && s <= 15 ? "ok" : "bad");
}
function renderState(s) {
  state = s;
  watch(s);
  const gw = Boolean(s.gateway_online), bus = Boolean(s.rs485_ok), ok = gw && bus;
  $("sysDot").className = "sys " + (ok ? "ok" : "bad");
  $("sysText").textContent = !gw ? "Gateway offline" : !bus ? "Lỗi RS485" : "Hệ thống hoạt động tốt";
  const msg = !gw ? "Gateway đang offline. Lệnh điều khiển chưa thể gửi tới phần cứng." : !bus ? "Mất liên lạc RS485" + (s.last_error ? `: ${s.last_error}` : ".") : "";
  $("banner").hidden = !msg;
  $("banner").textContent = msg;
  const sf = safe(), warns = [];
  for (const k in SENS) {
    const S = SENS[k], v = s[k], lv = level(k, v);
    $("v-" + k).textContent = k === "light" && has(v) ? Math.round(v).toLocaleString("vi-VN") : num(v, S.d);
    setChip("c-" + k, lv);
    $("h-" + k).textContent = `Vùng an toàn: ${sf[k][0]} đến ${sf[k][1]} ${S.unit}`;
    if (lv && lv !== "ok") warns.push(`${S.name} ${lv === "high" ? "cao" : "thấp"}`);
  }
  $("hTemp").textContent = num(s.temperature);
  setChip("hChip", level("temperature", s.temperature));
  if (rules) {
    $("a-temperature").textContent = `Quạt tự bật từ ${rules.fan_on_temp}°C, tắt khi xuống ${rules.fan_off_temp}°C.`;
    $("a-light").textContent = `Đèn tự bật dưới ${rules.led_on_lux} lux, tắt khi lên ${rules.led_off_lux} lux.`;
  }
  const bar = $("okbar");
  bar.className = "okbar" + (warns.length ? " warn" : "");
  bar.textContent = !ok ? "" : warns.length ? `Cần chú ý: ${warns.join(", ")}.` : [s.temperature, s.humidity, s.light].some((v) => !has(v)) ? "" : "Tất cả thông số đều nằm trong vùng an toàn ✓";
  renderDev("fan", s.fan_state, s.fan_mode);
  renderDev("led", s.led_state, s.led_mode);
  $("m-gw").textContent = gw ? "Đang kết nối" : "Mất kết nối"; $("m-gw").className = "st " + (gw ? "ok" : "bad");
  $("m-bus").textContent = bus ? "Ổn định" : "Lỗi"; $("m-bus").className = "st " + (bus ? "ok" : "bad");
  $("liveList").innerHTML = Object.keys(SENS).map((k) => {
    const lv = level(k, s[k]);
    return `<li><span>${SENS[k].icon} ${SENS[k].name}</span><b>${num(s[k], SENS[k].d)} ${SENS[k].unit} <i class="chip ${lv || ""}">${lv ? LV[lv] : "Không có số đo"}</i></b></li>`;
  }).join("");
  const alive = (v) => (has(v) && ok ? "Nhận dữ liệu" : "Mất tín hiệu");
  $("devList").innerHTML = `<li><span>Cảm biến nhiệt độ, độ ẩm</span><b>${alive(s.temperature)}</b></li><li><span>Cảm biến ánh sáng</span><b>${alive(s.light)}</b></li><li><span>Relay quạt</span><b>${ok ? (s.fan_state ? "Đang đóng" : "Đang mở") : "Mất tín hiệu"}</b></li><li><span>Relay đèn LED</span><b>${ok ? (s.led_state ? "Đang đóng" : "Đang mở") : "Mất tín hiệu"}</b></li>`;
  updateAge();
}

/* ---------- vẽ biểu đồ (canvas, không cần thư viện ngoài) ---------- */
function plot(cv, pts, o) {
  const box = cv.getBoundingClientRect();
  if (!box.width) return null;
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.round(box.width * dpr);
  cv.height = Math.round(box.height * dpr);
  const c = cv.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = box.width, H = box.height, L = o.mini ? 4 : 44, R = o.mini ? 4 : 10, T = 10, B = o.mini ? 6 : 22;
  const X = (t) => L + ((t - o.t0) / (o.t1 - o.t0)) * (W - L - R);
  const mute = css("--mute");
  c.font = "11px system-ui, sans-serif"; c.textBaseline = "middle";
  const marks = o.mini ? [] : o.marks || [];
  const vs = pts.map((p) => p.v).concat(marks);
  if (!vs.length) { c.fillStyle = mute; c.textAlign = "center"; c.fillText("Chưa có dữ liệu", W / 2, H / 2); return null; }
  let lo = Math.min(...vs), hi = Math.max(...vs);
  const pd = (hi - lo || 1) * 0.15; lo -= pd; hi += pd;
  const Y = (v) => H - B - ((v - lo) / (hi - lo)) * (H - B - T);
  if (!o.mini) {
    c.strokeStyle = css("--line"); c.fillStyle = mute; c.textAlign = "right"; c.lineWidth = 1;
    for (let n = 0; n < 4; n++) { const v = lo + ((hi - lo) * n) / 3; c.beginPath(); c.moveTo(L, Y(v)); c.lineTo(W - R, Y(v)); c.stroke(); c.fillText(num(v, o.d), L - 6, Y(v)); }
    (o.ticks || []).forEach((k, i, a) => { c.textAlign = i === 0 ? "left" : i === a.length - 1 ? "right" : "center"; c.fillText(k.label, X(k.t), H - 8); });
    c.setLineDash([5, 4]); c.strokeStyle = mute;
    marks.forEach((v) => { c.beginPath(); c.moveTo(L, Y(v)); c.lineTo(W - R, Y(v)); c.stroke(); });
    c.setLineDash([]);
  }
  c.strokeStyle = css(o.color); c.lineWidth = 2; c.lineJoin = "round"; c.beginPath();
  let last = null;
  for (const p of pts) { const x = X(p.t), y = Y(p.v); if (last === null || p.t - last > o.gap) c.moveTo(x, y); else c.lineTo(x, y); last = p.t; }
  c.stroke();
  return { X, Y, c, L, R, W, H };
}

function renderHistory() {
  const t0 = new Date(hDate + "T00:00:00").getTime(), S = SENS[hKey];
  const pts = hPts.filter((p) => has(p[hKey])).map((p) => ({ t: p.t, v: p[hKey] }));
  const ticks = [0, 6, 12, 18, 24].map((h) => ({ t: t0 + h * 3600000, label: pad(h % 24 || (h ? 0 : 0)) + ":00" }));
  ticks[4].label = "24:00";
  const marks = hKey === "temperature" && rules ? [rules.fan_off_temp, rules.fan_on_temp] : hKey === "light" && rules ? [rules.led_on_lux, rules.led_off_lux] : [];
  const v = plot($("hChart"), pts, { t0, t1: t0 + 86400000, color: S.color, d: S.d, marks, ticks, gap: Math.max(1800000, ((hSpan * 60000) / 480) * 4) });
  hView = v ? { t0, t1: t0 + 86400000, L: v.L, R: v.R, W: v.W } : null;
  if (v && hover && has(hover[hKey])) {
    const x = v.X(hover.t);
    v.c.strokeStyle = css("--mute"); v.c.beginPath(); v.c.moveTo(x, 0); v.c.lineTo(x, v.H - 22); v.c.stroke();
    v.c.fillStyle = css(S.color); v.c.beginPath(); v.c.arc(x, v.Y(hover[hKey]), 4, 0, Math.PI * 2); v.c.fill();
  }
  $("readout").textContent = hover ? `${hm(hover.t)}: ` + Object.keys(SENS).map((k) => `${SENS[k].name} ${num(hover[k], SENS[k].d)} ${SENS[k].unit}`).join("   ") : "Rê chuột hoặc chạm vào biểu đồ để xem giá trị tại từng thời điểm.";
  const [y, m, d] = hDate.split("-");
  $("tblTitle").textContent = `Dữ liệu chi tiết (${d}/${m}/${y})`;
  const H = Array.from({ length: 24 }, () => ({ temperature: [], humidity: [], light: [] }));
  for (const p of hPts) { const h = new Date(p.t).getHours(); for (const k in SENS) if (has(p[k])) H[h][k].push(p[k]); }
  const isToday = hDate === ymd(Date.now()), nowH = new Date().getHours();
  const avg = (a, d) => (a.length ? (a.reduce((x, z) => x + z, 0) / a.length).toFixed(d) : "—");
  let rows = "";
  for (let h = 0; h < 24; h++) {
    if (isToday && h > nowH) break;
    const cur = isToday && h === nowH;
    rows += `<tr><td${cur ? ' class="now"' : ""}>${pad(h)}:00 đến ${pad((h + 1) % 24)}:00${cur ? " (đang tính)" : ""}</td><td>${avg(H[h].temperature, 1)}</td><td>${avg(H[h].humidity, 0)}</td><td>${avg(H[h].light, 0)}</td></tr>`;
  }
  $("tbl").innerHTML = rows;
}
async function loadHistory() {
  const t0 = new Date(hDate + "T00:00:00").getTime();
  hSpan = Math.min(10080, Math.ceil((Date.now() - t0) / 60000) + 5);
  const rows = await fetchJson(`/api/history?minutes=${hSpan}&max_points=480`);
  hPts = rows.map((r) => ({ ...r, t: Date.parse(r.timestamp) })).filter((p) => p.t >= t0 && p.t < t0 + 86400000);
  hover = null;
  renderHistory();
}
function setDate(str) {
  const min = ymd(Date.now() - 6 * 86400000), max = ymd(Date.now());
  hDate = str < min ? min : str > max ? max : str;
  $("dDate").value = hDate;
  loadHistory().catch(console.error);
}
function shiftDate(n) { setDate(ymd(new Date(hDate + "T12:00:00").getTime() + n * 86400000)); }

async function loadSpark() {
  const now = Date.now();
  const rows = await fetchJson("/api/history?minutes=30&max_points=120");
  spk = { now, pts: rows.map((r) => ({ ...r, t: Date.parse(r.timestamp) })) };
  drawSpark();
}
function drawSpark() {
  if (!spk) return;
  for (const k in SENS) {
    const S = SENS[k], pts = spk.pts.filter((p) => has(p[k])).map((p) => ({ t: p.t, v: p[k] }));
    plot($("spark-" + k), pts, { mini: true, t0: spk.now - 1800000, t1: spk.now, color: S.color, gap: 180000 });
    const vs = pts.map((p) => p.v);
    $("sp-" + k).textContent = vs.length ? `thấp nhất ${num(Math.min(...vs), S.d)}, cao nhất ${num(Math.max(...vs), S.d)} ${S.unit}` : "chưa có dữ liệu";
  }
}

/* ---------- điều khiển ---------- */
async function control(d, mode, st) {
  $("dev-" + d).classList.add("busy");
  authBlocked = false;
  try {
    const res = await fetchJson(`/api/control/${d}`, { method: "POST", body: JSON.stringify({ mode, state: st }) });
    if (!res.accepted) throw new Error(res.message || "Lệnh bị từ chối");
    intent[d] = { mode, state: st };
    clearTimeout(pending[d]);
    pending[d] = setTimeout(() => { done(d); toast(`${DEV[d].name}: gateway chưa phản hồi lệnh`, true); }, 8000);
  } catch (e) {
    done(d);
    toast(e.message, true);
    if (state) renderDev(d, state[d + "_state"], state[d + "_mode"]);
  }
}

/* ---------- ngưỡng tự động và vùng an toàn ---------- */
function formRules() { const f = {}; for (const [k, id] of Object.entries(RULE_IDS)) f[k] = $(id).value === "" ? NaN : Number($(id).value); return f; }
function fillRules() { if (rules) for (const [k, id] of Object.entries(RULE_IDS)) $(id).value = rules[k]; }
function checkRules() {
  const f = formRules();
  let err = "";
  if (!Object.values(f).every(Number.isFinite)) err = "Nhập đủ bốn giá trị.";
  else if (f.fan_off_temp >= f.fan_on_temp) err = "Nhiệt độ tắt quạt phải thấp hơn nhiệt độ bật quạt.";
  else if (f.led_on_lux >= f.led_off_lux) err = "Ngưỡng bật đèn phải thấp hơn ngưỡng tắt đèn.";
  const dirty = Boolean(rules) && Object.keys(f).some((k) => f[k] !== rules[k]);
  $("rulesMsg").textContent = err;
  $("rulesMsg").className = "msg" + (err ? " bad" : "");
  $("saveRules").disabled = Boolean(err) || !dirty;
  $("resetRules").disabled = !dirty;
}
async function loadRules() { rules = await fetchJson("/api/rules"); fillRules(); checkRules(); if (state) renderState(state); }
async function saveRules() {
  const f = formRules();
  authBlocked = false;
  $("saveRules").disabled = true;
  try {
    const res = await fetchJson("/api/rules", { method: "PUT", body: JSON.stringify(f) });
    rules = f;
    toast(res.gateway_applied ? "Đã lưu và áp dụng cho gateway" : "Đã lưu. Gateway sẽ nhận ngưỡng khi kết nối lại");
    if (state) renderState(state);
  } catch (e) { toast(e.message, true); }
  checkRules();
}
function fillSafe() { const s = safe(); for (const k in SAFE_IDS) { $(SAFE_IDS[k][0]).value = s[k][0]; $(SAFE_IDS[k][1]).value = s[k][1]; } }
function saveSafe() {
  const out = {};
  for (const k in SAFE_IDS) {
    const a = Number($(SAFE_IDS[k][0]).value), b = Number($(SAFE_IDS[k][1]).value);
    if (!Number.isFinite(a) || !Number.isFinite(b) || a >= b) { $("safeMsg").textContent = `${SENS[k].name}: giá trị thấp nhất phải nhỏ hơn giá trị cao nhất.`; $("safeMsg").className = "msg bad"; return; }
    out[k] = [a, b];
  }
  store("gh_safe", out);
  $("safeMsg").textContent = "";
  toast("Đã lưu vùng an toàn");
  Object.keys(prev).forEach((k) => delete prev[k]);
  if (state) renderState(state);
}
function applyTheme(v) {
  document.documentElement.dataset.theme = v === "auto" ? "" : v;
  document.querySelectorAll("#themeSeg button").forEach((b) => b.classList.toggle("active", b.dataset.v === v));
  store("gh_theme", v);
  route();
}

/* ---------- điều hướng ---------- */
let simLoaded = false, simDispose = null;
function route() {
  const p = PAGES.includes(location.hash.slice(1)) ? location.hash.slice(1) : "overview";
  PAGES.forEach((x) => ($("pg-" + x).hidden = x !== p));
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.p === p));
  $("pgTitle").textContent = INFO[p][0];
  $("pgSub").textContent = INFO[p][1];
  if (p === "alerts") { store("gh_seen", Date.now()); }
  renderBadge();
  // Dispose simulation when leaving tab
  if (p !== "simulation" && simDispose) { simDispose(); simDispose = null; }
  requestAnimationFrame(() => {
    if (p === "history") loadHistory().catch(console.error);
    if (p === "monitor") loadSpark().catch(console.error);
    if (p === "simulation" && !simDispose) {
      import("/sim/sim.js").then(mod => {
        mod.initSimulation();
        simDispose = mod.disposeSimulation;
        simLoaded = true;
      }).catch(e => console.error("[Sim] load failed:", e));
    }
  });
}

/* ---------- thời gian thực ---------- */
function connectWebSocket() {
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/live`);
  let sent = "";
  ws.onopen = () => { sent = getToken(); ws.send(JSON.stringify({ type: "auth", token: sent })); };
  ws.onmessage = (event) => {
    try {
      const p = JSON.parse(event.data);
      if (p.type === "command_ack") {
        if (DEV[p.device]) done(p.device);
        if (!p.ok) toast(`Lệnh thất bại: ${p.message}`, true);
        loadState().catch(console.error);
        return;
      }
      if (p.type === "gateway_event") { if (p.level === "error" || p.level === "warning") addEvent("warn", `Gateway: ${p.message}`); return; }
      renderState(p);
    } catch { /* bỏ qua tin nhắn lỗi */ }
  };
  ws.onclose = async (event) => {
    if (event.code === 1008) {
      if (getToken() === sent) localStorage.removeItem(TOKEN_KEY);
      const token = getToken() || (await ensureToken("Mã truy cập bị từ chối. Nhập lại mã truy cập."));
      if (!token) { wsStopped = true; return; }
    }
    setTimeout(connectWebSocket, 2000);
  };
  ws.onerror = () => ws.close();
}
async function loadState() { renderState(await fetchJson("/api/state")); }

/* ---------- khởi động ---------- */
document.querySelectorAll(".mode button").forEach((b) => b.addEventListener("click", () => {
  const d = b.dataset.dev;
  control(d, b.dataset.mode, b.dataset.mode === "AUTO" ? null : Boolean(state && state[d + "_state"]));
}));
["fan", "led"].forEach((d) => $("sw-" + d).addEventListener("change", (e) => control(d, "MANUAL", e.target.checked)));
$("bell").addEventListener("click", () => (location.hash = "#alerts"));
$("hTabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; hKey = b.dataset.k; hover = null; document.querySelectorAll("#hTabs button").forEach((x) => x.classList.toggle("active", x === b)); renderHistory(); });
$("aTabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; alertTab = b.dataset.t; document.querySelectorAll("#aTabs button").forEach((x) => x.classList.toggle("active", x === b)); renderAlerts(); });
$("clearEv").addEventListener("click", () => { events = []; store("gh_events", events); renderAlerts(); renderBadge(); });
$("dPrev").addEventListener("click", () => shiftDate(-1));
$("dNext").addEventListener("click", () => shiftDate(1));
$("dToday").addEventListener("click", () => setDate(ymd(Date.now())));
$("dDate").addEventListener("change", (e) => e.target.value && setDate(e.target.value));
$("hChart").addEventListener("pointermove", (e) => {
  if (!hView || !hPts.length) return;
  const box = $("hChart").getBoundingClientRect();
  const t = hView.t0 + ((e.clientX - box.left - hView.L) / (hView.W - hView.L - hView.R)) * (hView.t1 - hView.t0);
  hover = hPts.reduce((best, p) => (Math.abs(p.t - t) < Math.abs(best.t - t) ? p : best), hPts[0]);
  renderHistory();
});
$("hChart").addEventListener("pointerleave", () => { hover = null; renderHistory(); });
Object.values(RULE_IDS).forEach((id) => $(id).addEventListener("input", checkRules));
$("rulesForm").addEventListener("submit", (e) => { e.preventDefault(); if (!$("saveRules").disabled) saveRules(); });
$("resetRules").addEventListener("click", () => { fillRules(); checkRules(); });
$("safeForm").addEventListener("submit", (e) => { e.preventDefault(); saveSafe(); });
$("themeSeg").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) applyTheme(b.dataset.v); });
$("logout").addEventListener("click", () => { localStorage.removeItem(TOKEN_KEY); location.reload(); });
window.addEventListener("hashchange", route);
window.addEventListener("resize", () => { if (!$("pg-history").hidden) renderHistory(); if (!$("pg-monitor").hidden) drawSpark(); });

(async function init() {
  fillSafe();
  applyTheme(store("gh_theme") || "auto");
  renderAlerts();
  $("dDate").max = ymd(Date.now());
  $("dDate").min = ymd(Date.now() - 6 * 86400000);
  $("dDate").value = hDate;
  await Promise.allSettled([loadState(), loadRules()]);
  connectWebSocket();
  setInterval(() => { $("clock").textContent = new Date().toLocaleString("vi-VN"); updateAge(); }, 1000);
  setInterval(() => { if (!authBlocked) loadState().catch(() => {}); }, 5000);
  setInterval(() => { if (!authBlocked && !$("pg-history").hidden && hDate === ymd(Date.now())) loadHistory().catch(console.error); }, 60000);
  setInterval(() => { if (!authBlocked && !$("pg-monitor").hidden) loadSpark().catch(console.error); }, 30000);
})();
