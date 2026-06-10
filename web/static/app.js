"use strict";

const TEST_API_URL = "http://api-test03.ucloudadmin.com";

const state = {
  config: { env: "prod", public_key: "", private_key: "", project_ids: "", api_url: "" },
  regions: {},
  resources: [],
  selectedRegions: new Set(),
  selectedResources: new Set(),
  tasks: { running: null, pending: [], history: [] },
  subscriptions: {},
  logCollapsed: {},   // task_id -> bool；默认展开
  logCounts: {},      // task_id -> 累计日志行数（前端显示）
};

const $ = (sel) => document.querySelector(sel);

// ---------- localStorage ----------
const STORAGE_KEY = "ucc-web-config";

function saveConfig() {
  const data = {
    env: state.config.env,
    public_key: state.config.public_key,
    project_ids: state.config.project_ids,
    api_url: state.config.api_url,
    selectedRegions: [...state.selectedRegions],
    selectedResources: [...state.selectedResources],
    // 私钥不持久化
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.env) state.config.env = data.env;
    state.config.public_key = data.public_key || "";
    state.config.project_ids = data.project_ids || "";
    state.config.api_url = data.api_url || "";
    state.selectedRegions = new Set(data.selectedRegions || []);
    state.selectedResources = new Set(data.selectedResources || []);
  } catch (e) {
    console.warn("loadConfig failed", e);
  }
}

// ---------- API ----------
async function api(path, opts = {}) {
  const resp = await fetch(path, opts);
  const ct = resp.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await resp.json() : await resp.text();
  if (!resp.ok) throw new Error((body && body.error) || `HTTP ${resp.status}`);
  return body;
}

async function loadRegions() {
  state.regions = await api(`/api/regions?env=${state.config.env}`);
  renderRegions();
}

async function loadResources() {
  state.resources = await api("/api/resources");
  renderResources();
}

async function loadSnapshot() {
  const snap = await api("/api/snapshot");
  state.tasks = snap;
  renderTasks();
}

// ---------- 渲染 ----------
function renderRegions() {
  const root = $("#regions");
  root.innerHTML = "";
  for (const name of Object.keys(state.regions)) {
    const id = `r-${name}`;
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.id = id; cb.checked = state.selectedRegions.has(name);
    cb.addEventListener("change", () => {
      cb.checked ? state.selectedRegions.add(name) : state.selectedRegions.delete(name);
      saveConfig();
    });
    label.appendChild(cb);
    label.appendChild(document.createTextNode(name));
    root.appendChild(label);
  }
}

function renderResources() {
  const root = $("#resources");
  root.innerHTML = "";
  for (const name of state.resources) {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = state.selectedResources.has(name);
    cb.addEventListener("change", () => {
      cb.checked ? state.selectedResources.add(name) : state.selectedResources.delete(name);
      saveConfig();
    });
    label.appendChild(cb);
    label.appendChild(document.createTextNode(name));
    root.appendChild(label);
  }
}

function renderTasks() {
  renderRunning();
  renderPending();
  renderHistory();
  const pendCount = (state.tasks.pending || []).length;
  $("#queue-badge").textContent = `队列: ${pendCount + (state.tasks.running ? 1 : 0)}`;
  $("#pending-count").textContent = `(${pendCount})`;
  $("#history-count").textContent = `(${(state.tasks.history || []).length})`;
}

function statusTag(state_) {
  return `<span class="status-tag status-${state_}">${state_}</span>`;
}

function renderRunning() {
  const root = $("#running-block");
  const t = state.tasks.running;
  if (!t) {
    root.innerHTML = '<p class="empty-hint">暂无运行中的任务</p>';
    return;
  }
  const collapsed = !!state.logCollapsed[t.task_id];
  const count = state.logCounts[t.task_id] || 0;
  root.innerHTML = `
    <div class="task-card" data-task="${t.task_id}">
      <div class="meta">
        ${statusTag(t.state)} <code>${t.task_id}</code> · ${t.selected_regions.length} 区域 · ${t.selected_resources.length} 资源
      </div>
      <div class="log-section ${collapsed ? "collapsed" : ""}" data-task="${t.task_id}">
        <div class="log-header" data-action="toggle" data-task="${t.task_id}">
          <span class="log-caret">${collapsed ? "▸" : "▾"}</span>
          <span class="log-title">实时日志</span>
          <span class="log-count" id="log-count-${t.task_id}">${count} 条</span>
          <div class="log-header-actions" data-stop-propagation>
            <label><input type="checkbox" id="autoscroll-${t.task_id}" checked /> 自动滚动</label>
            <button class="btn btn-secondary btn-sm" data-action="clear" data-task="${t.task_id}">清空显示</button>
          </div>
        </div>
        <div class="log-panel" id="log-${t.task_id}"></div>
      </div>
      <div class="actions">
        <button class="btn btn-danger" data-action="stop" data-task="${t.task_id}">停止</button>
      </div>
    </div>`;
  // 确保已订阅 SSE
  ensureSubscribed(t.task_id);
}

function renderPending() {
  const root = $("#pending-list");
  if (!state.tasks.pending.length) { root.innerHTML = '<p class="empty-hint">无</p>'; return; }
  root.innerHTML = state.tasks.pending.map((t, i) => `
    <div class="task-card">
      <div class="meta">
        ${statusTag(t.state)} <code>${t.task_id}</code> · 位置 ${i + (state.tasks.running ? 1 : 0)}
      </div>
      <div class="actions">
        <button class="btn btn-danger" data-action="stop" data-task="${t.task_id}">取消</button>
      </div>
    </div>`).join("");
}

function renderHistory() {
  const root = $("#history-list");
  if (!state.tasks.history.length) { root.innerHTML = '<p class="empty-hint">无</p>'; return; }
  root.innerHTML = state.tasks.history.slice().reverse().map(t => `
    <div class="task-card">
      <div class="meta">
        ${statusTag(t.state)} <code>${t.task_id}</code> · ${new Date(t.finished_at * 1000).toLocaleString()}
      </div>
    </div>`).join("");
}

// ---------- 事件委托 ----------
document.addEventListener("click", async (e) => {
  // 折叠头点击：展开/收起日志面板
  const header = e.target.closest("[data-action='toggle']");
  if (header && !e.target.closest("[data-stop-propagation]")) {
    const taskId = header.dataset.task;
    const section = header.closest(".log-section");
    if (section) {
      section.classList.toggle("collapsed");
      const collapsed = section.classList.contains("collapsed");
      state.logCollapsed[taskId] = collapsed;
      const caret = section.querySelector(".log-caret");
      if (caret) caret.textContent = collapsed ? "▸" : "▾";
    }
    return;
  }
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const taskId = btn.dataset.task;
  if (btn.dataset.action === "stop") {
    try {
      await api(`/api/tasks/${taskId}/stop`, { method: "POST" });
      await loadSnapshot();
    } catch (err) {
      alert(err.message);
    }
  } else if (btn.dataset.action === "clear") {
    const pane = $(`#log-${taskId}`);
    if (pane) pane.innerHTML = "";
    state.logCounts[taskId] = 0;
    const badge = $(`#log-count-${taskId}`);
    if (badge) badge.textContent = "0 条";
  }
});

// ---------- SSE ----------
function ensureSubscribed(taskId) {
  if (state.subscriptions[taskId]) return;
  const es = new EventSource(`/api/tasks/${taskId}/stream`);
  state.subscriptions[taskId] = es;

  es.addEventListener("log", (ev) => appendLog(taskId, JSON.parse(ev.data)));
  es.addEventListener("state", (ev) => {
    const data = JSON.parse(ev.data);
    console.log(`[${taskId}] state →`, data);
  });
  es.addEventListener("end", async () => {
    es.close();
    delete state.subscriptions[taskId];
    await loadSnapshot();
  });
  es.addEventListener("heartbeat", () => { /* noop */ });
  es.onerror = () => console.warn(`SSE error for ${taskId}; 浏览器将自动重连`);
}

function appendLog(taskId, item) {
  const pane = $(`#log-${taskId}`);
  if (!pane) return;
  const div = document.createElement("div");
  div.className = `line ${item.level || "INFO"}`;
  const ts = new Date((item.ts || 0) * 1000).toLocaleTimeString();
  div.textContent = `${ts} [${item.level}] ${item.line}`;
  pane.appendChild(div);
  // 累计行数 + 徽章
  state.logCounts[taskId] = (state.logCounts[taskId] || 0) + 1;
  const badge = $(`#log-count-${taskId}`);
  if (badge) badge.textContent = `${state.logCounts[taskId]} 条`;
  // 自动滚动（即使折叠也保持滚动位置在末尾，展开时立刻看到最新）
  const auto = $(`#autoscroll-${taskId}`);
  if (auto && auto.checked) pane.scrollTop = pane.scrollHeight;
}

// ---------- 表单 ----------
function bindForm() {
  $("#env-select").value = state.config.env;
  $("#public-key").value = state.config.public_key;
  $("#project-ids").value = state.config.project_ids;
  $("#api-url").value = state.config.api_url;

  $("#env-select").addEventListener("change", async (e) => {
    state.config.env = e.target.value;
    state.selectedRegions = new Set();
    // 测试环境：若用户未填 api_url，自动填入测试 endpoint（可见可改）
    if (state.config.env === "test" && !state.config.api_url.trim()) {
      state.config.api_url = TEST_API_URL;
      $("#api-url").value = TEST_API_URL;
    }
    saveConfig();
    await loadRegions();
  });
  $("#public-key").addEventListener("input", (e) => { state.config.public_key = e.target.value; saveConfig(); });
  $("#private-key").addEventListener("input", (e) => { state.config.private_key = e.target.value; /* 不存 */ });
  $("#project-ids").addEventListener("input", (e) => { state.config.project_ids = e.target.value; saveConfig(); });
  $("#api-url").addEventListener("input", (e) => { state.config.api_url = e.target.value; saveConfig(); });

  $("#submit-btn").addEventListener("click", onSubmit);
}

async function onSubmit() {
  const err = $("#submit-error"); err.textContent = "";
  const payload = {
    env_name: state.config.env === "test" ? "测试环境" : "正式环境",
    public_key: state.config.public_key.trim(),
    private_key: state.config.private_key,
    project_ids: state.config.project_ids.split(",").map(s => s.trim()).filter(Boolean),
    selected_regions: [...state.selectedRegions],
    selected_resources: [...state.selectedResources],
    api_url: state.config.api_url.trim(),
  };
  if (!payload.public_key) return err.textContent = "请填公钥";
  if (!payload.private_key) return err.textContent = "请填私钥";
  if (!payload.project_ids.length) return err.textContent = "请填项目 ID";
  if (!payload.selected_regions.length) return err.textContent = "请至少勾选 1 个区域";
  if (!payload.selected_resources.length) return err.textContent = "请至少勾选 1 个资源类型";

  try {
    const res = await api("/api/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    ensureSubscribed(res.task_id);
    await loadSnapshot();
  } catch (e) {
    err.textContent = e.message;
  }
}

// ---------- 启动 ----------
async function main() {
  loadConfig();
  bindForm();
  await Promise.all([loadRegions(), loadResources(), loadSnapshot()]);
  if (state.tasks.running) ensureSubscribed(state.tasks.running.task_id);
}

main();
