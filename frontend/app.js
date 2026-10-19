let chart;
let ws;

const $ = (id) => document.getElementById(id);

function setText(id, value) {
    $(id).textContent = value;
}

function renderState(state) {
    const has = (value) => value !== null && value !== undefined;
    setText("temperature", has(state.temperature) ? Number(state.temperature).toFixed(1) : "--");
    setText("humidity", has(state.humidity) ? Number(state.humidity).toFixed(1) : "--");
    setText("light", has(state.light) ? Math.round(state.light).toLocaleString("en-US") : "--");
    setText("fanState", state.fan_state ? "ON" : "OFF");
    setText("ledState", state.led_state ? "ON" : "OFF");
    setText("fanMode", state.fan_mode);
    setText("ledMode", state.led_mode);
    setText("rs485Status", state.rs485_ok ? "OK" : "ERROR");

    const online = Boolean(state.gateway_online);
    $("gatewayDot").classList.toggle("online", online);
    $("gatewayDot").classList.toggle("offline", !online);
    setText("gatewayStatus", online ? "Gateway Online" : "Gateway Offline");
}

const TOKEN_KEY = "greenhouse_access_token";

let tokenPrompt = null;   // one prompt at a time, shared by every request that gets a 401
let authBlocked = false;  // token missing/rejected and the user cancelled: pause polling until they act again
let wsStopped = false;    // the realtime socket gave up because it had no valid token

function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
}

function askToken(message) {
    const value = (window.prompt(message) || "").trim();
    if (value) {
        localStorage.setItem(TOKEN_KEY, value);
    }
    return value;
}

function ensureToken(message = "Enter the dashboard access token:") {
    if (!tokenPrompt) {
        tokenPrompt = Promise.resolve()
            .then(() => {
                const value = askToken(message);
                authBlocked = !value;
                if (value && wsStopped) {
                    wsStopped = false;
                    connectWebSocket();
                }
                return value;
            })
            .finally(() => {
                tokenPrompt = null;
            });
    }
    return tokenPrompt;
}

async function fetchJson(url, options = {}, retry = true) {
    const sentToken = getToken();
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(sentToken ? { Authorization: `Bearer ${sentToken}` } : {}),
            ...(options.headers || {}),
        },
    });

    if (response.status === 401 && retry) {
        if (getToken() === sentToken) {
            localStorage.removeItem(TOKEN_KEY);  // the token we sent was just rejected
        }
        const token = getToken() || (await ensureToken());
        if (token && token !== sentToken) {
            return fetchJson(url, options, false);
        }
        authBlocked = true;
    }

    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

async function loadState() {
    const state = await fetchJson("/api/state");
    renderState(state);
}

async function loadRules() {
    const rules = await fetchJson("/api/rules");
    $("fanOnTemp").value = rules.fan_on_temp;
    $("fanOffTemp").value = rules.fan_off_temp;
    $("ledOnLux").value = rules.led_on_lux;
    $("ledOffLux").value = rules.led_off_lux;
}

function sampleRows(rows, maxPoints = 360) {
    if (rows.length <= maxPoints) {
        return rows;
    }

    const step = (rows.length - 1) / (maxPoints - 1);
    const sampled = [];

    for (let i = 0; i < maxPoints; i += 1) {
        sampled.push(rows[Math.round(i * step)]);
    }

    return sampled;
}

async function waitForChart(timeoutMs = 5000) {
    const start = Date.now();
    while (typeof Chart === "undefined" && Date.now() - start < timeoutMs) {
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return typeof Chart !== "undefined";
}

function initHistoryChart() {
    const ctx = $("historyChart").getContext("2d");

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Temperature (°C)",
                    data: [],
                    yAxisID: "y",
                    tension: 0.25,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: "Humidity (%RH)",
                    data: [],
                    yAxisID: "y",
                    tension: 0.25,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: "Light (Lux)",
                    data: [],
                    yAxisID: "y1",
                    tension: 0.25,
                    pointRadius: 0,
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            normalized: true,
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: {
                    position: "top",
                },
            },
            scales: {
                x: {
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 9,
                        maxRotation: 0,
                    },
                    grid: {
                        display: false,
                    },
                },
                y: {
                    position: "left",
                    beginAtZero: false,
                    grace: "5%",
                },
                y1: {
                    position: "right",
                    beginAtZero: false,
                    grace: "5%",
                    grid: {
                        drawOnChartArea: false,
                    },
                },
            },
        },
    });
}

async function loadHistory() {
    if (!chart) {
        return;  // Chart.js did not load
    }

    const minutes = Number($("historyRange").value);
    const rows = await fetchJson(`/api/history?minutes=${minutes}&max_points=360`);
    const sampled = sampleRows(rows, 360);

    chart.data.labels = sampled.map((row) => new Date(row.timestamp).toLocaleTimeString());
    chart.data.datasets[0].data = sampled.map((row) => row.temperature);
    chart.data.datasets[1].data = sampled.map((row) => row.humidity);
    chart.data.datasets[2].data = sampled.map((row) => row.light);
    chart.update("none");
}

async function sendControl(device, mode, state = null) {
    authBlocked = false;
    const response = await fetchJson(`/api/control/${device}`, {
        method: "POST",
        body: JSON.stringify({ mode, state }),
    });

    if (!response.accepted) {
        throw new Error(response.message || "Command rejected");
    }

    await loadState();
}

async function saveRules() {
    authBlocked = false;
    const payload = {
        fan_on_temp: Number($("fanOnTemp").value),
        fan_off_temp: Number($("fanOffTemp").value),
        led_on_lux: Number($("ledOnLux").value),
        led_off_lux: Number($("ledOffLux").value),
    };

    try {
        await fetchJson("/api/rules", {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        $("rulesMessage").textContent = "Saved";
        setTimeout(() => {
            $("rulesMessage").textContent = "";
        }, 1500);
    } catch (error) {
        $("rulesMessage").textContent = error.message;
    }
}

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${protocol}://${location.host}/ws/live`);

    let sentToken = "";

    ws.onopen = () => {
        sentToken = getToken();
        ws.send(JSON.stringify({ type: "auth", token: sentToken }));
    };

    ws.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            if (payload.type === "command_ack") {
                console.info(`[GATEWAY ACK] ${payload.device}: ${payload.message}`);
                if (!payload.ok) {
                    alert(`Hardware command failed: ${payload.message}`);
                }
                loadState().catch(console.error);
                return;
            }
            if (payload.type === "gateway_event") {
                console.info(`[GATEWAY ${payload.level}] ${payload.message}`);
                return;
            }
            renderState(payload);
        } catch {
            // Ignore malformed realtime messages.
        }
    };

    ws.onclose = async (event) => {
        if (event.code === 1008) {  // token rejected
            if (getToken() === sentToken) {
                localStorage.removeItem(TOKEN_KEY);
            }
            const token = getToken() || (await ensureToken("Access token rejected. Enter the dashboard access token:"));
            if (!token) {
                wsStopped = true;  // a later successful prompt restarts the socket
                return;
            }
        }
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

document.querySelectorAll(".mode-btn").forEach((button) => {
    button.addEventListener("click", async () => {
        const device = button.dataset.device;
        const mode = button.dataset.mode;
        const rawState = button.dataset.state;
        const state = rawState === undefined ? null : rawState === "true";

        button.disabled = true;

        try {
            await sendControl(device, mode, state);
        } catch (error) {
            alert(error.message);
        } finally {
            button.disabled = false;
        }
    });
});

$("historyRange").addEventListener("change", () => {
    authBlocked = false;
    loadHistory().catch(console.error);
});
$("saveRules").addEventListener("click", saveRules);

(async function init() {
    if (await waitForChart()) {
        initHistoryChart();
    } else {
        $("historyChart").parentElement.textContent =
            "Chart.js could not be loaded (no internet?). Put chart.umd.js into the frontend folder.";
    }

    try {
        await Promise.all([loadState(), loadRules(), loadHistory()]);
    } catch (error) {
        console.error(error);
    }

    connectWebSocket();
    setInterval(() => {
        if (!authBlocked) {
            loadHistory().catch(console.error);
        }
    }, 10000);
    setInterval(() => {
        if (!authBlocked) {
            loadState().catch(() => {});
        }
    }, 5000);
})();
