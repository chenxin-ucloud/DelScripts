"use strict";

const state = {
  config: { env: "prod", public_key: "", private_key: "" },
  projects: [],          // [{project_id, name, create_time}, ...]
  selectedProjects: new Set(),
  regions: {},
  resources: [],
  selectedRegions: new Set(),
  selectedResources: new Set(),
  tasks: { running: null, pending: [], history: [] },
  subscriptions: {},
  historyCollapsed: {},  // task_id -> bool；默认收起
  currentLogTaskId: null,
  logCount: 0,
};

const $ = (sel) => document.querySelector(sel);

// ---------- localStorage ----------
const STORAGE_KEY = "ucc-web-config";

function saveConfig() {
  const data = {
    env: state.config.env,
    public_key: state.config.public_key,
    selectedProjects: [...state.selectedProjects],
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
    state.selectedProjects = new Set(data.selectedProjects || []);
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

async function fetchProjects() {
  const msg = $("#projects-msg");
  msg.textContent = "加载中...";
  try {
    const body = await api("/api/projects", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        public_key: state.config.public_key.trim(),
        private_key: state.config.private_key,
        env_name: state.config.env === "test" ? "测试环境" : "正式环境",
      }),
    });
    state.projects = body.projects || [];
    // 自动保留之前已选且仍存在的项目
    const valid = new Set();
    for (const pid of state.selectedProjects) {
      if (state.projects.some((p) => p.project_id === pid)) valid.add(pid);
    }
    state.selectedProjects = valid;
    renderProjects();
    msg.textContent = state.projects.length
      ? `已加载 ${state.projects.length} 个项目`
      : "未获取到项目（请检查密钥）";
  } catch (e) {
    msg.textContent = e.message;
  }
}

// ---------- 渲染 ----------
function renderProjects() {
  const root = $("#projects");
  root.innerHTML = "";
  if (!state.projects.length) {
    root.innerHTML = '<p class="empty-hint">请先点击「获取项目」</p>';
    return;
  }
  for (const p of state.projects) {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = state.selectedProjects.has(p.project_id);
    cb.addEventListener("change", () => {
      cb.checked ? state.selectedProjects.add(p.project_id) : state.selectedProjects.delete(p.project_id);
      saveConfig();
    });
    label.appendChild(cb);
    label.appendChild(document.createTextNode(`${p.name} (${p.project_id})`));
    root.appendChild(label);
  }
}

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

function updateLogBadge() {
  const badge = $("#log-count");
  if (badge) badge.textContent = `${state.logCount} 条`;
}

function resetLogPanel(taskId) {
  const panel = $("#log-panel");
  if (panel) panel.innerHTML = "";
  state.currentLogTaskId = taskId;
  state.logCount = 0;
  updateLogBadge();
}

function renderRunning() {
  const root = $("#running-block");
  const t = state.tasks.running;
  if (!t) {
    root.innerHTML = '<p class="empty-hint">暂无运行中的任务</p>';
    return;
  }
  if (state.currentLogTaskId !== t.task_id) {
    resetLogPanel(t.task_id);
  }
  root.innerHTML = `
    <div class="task-card" data-task="${t.task_id}">
      <div class="meta">
        ${statusTag(t.state)} <code>${t.task_id}</code> · ${t.selected_regions.length} 区域 · ${t.selected_resources.length} 资源
      </div>
      <div class="actions">
        <button class="btn btn-danger" data-action="stop" data-task="${t.task_id}">停止</button>
      </div>
    </div>`;
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
  root.innerHTML = state.tasks.history.slice().reverse().map(t => {
    // 默认收起（state.historyCollapsed[task_id] 默认未设置，未设置即视为收起 true）
    const collapsed = state.historyCollapsed[t.task_id] !== false;
    // 标题栏：状态 + 项目名称(项目ID) 列表 + 完成时间
    const projectNames = t.project_ids.map(pid => {
      const info = state.projects.find(p => p.project_id === pid);
      const name = info ? info.name : pid;
      return `${name} (${pid})`;
    });
    const projectLabel = projectLabels(projectNames);
    const finishedAt = t.finished_at ? new Date(t.finished_at * 1000).toLocaleString() : '';
    return `
    <div class="task-card history-card ${collapsed ? 'collapsed' : ''}" data-task="${t.task_id}">
      <div class="history-header" data-action="toggle-history" data-task="${t.task_id}">
        <span class="log-caret">${collapsed ? '▸' : '▾'}</span>
        ${statusTag(t.state)}
        <span class="history-title">${projectLabel}</span>
        <span class="history-time">${finishedAt}</span>
      </div>
      <div class="details">
        <dl>
          <dt>Task ID</dt><dd><code>${t.task_id}</code></dd>
          <dt>环境</dt><dd>${t.env_name}</dd>
          <dt>项目</dt><dd><div class="tag-list">${projectNames.map(s => `<span class="tag">${s}</span>`).join('')}</div></dd>
          <dt>区域</dt><dd><div class="tag-list">${t.selected_regions.map(r => `<span class="tag">${r}</span>`).join('')}</div></dd>
          <dt>资源</dt><dd><div class="tag-list">${t.selected_resources.map(r => `<span class="tag">${r}</span>`).join('')}</div></dd>
          <dt>公钥</dt><dd>${t.public_key}</dd>
        </dl>
      </div>
    </div>`;
  }).join("");
}

// 项目名称列表的简短展示：1 个全显示，多个显示第一个 + 等 N 个
function projectLabels(names) {
  if (!names.length) return '无项目';
  if (names.length === 1) return names[0];
  return `${names[0]} 等 ${names.length} 个项目`;
}

// ---------- 事件：全局日志面板 ----------
$("#log-header").addEventListener("click", (e) => {
  if (e.target.closest(".log-header-actions")) return;
  const section = $("#log-section");
  section.classList.toggle("collapsed");
  const caret = $("#log-caret");
  if (caret) caret.textContent = section.classList.contains("collapsed") ? "▸" : "▾";
});

$("#clear-logs").addEventListener("click", () => {
  const pane = $("#log-panel");
  if (pane) pane.innerHTML = "";
  state.logCount = 0;
  updateLogBadge();
});

// ---------- 事件委托 ----------
document.addEventListener("click", async (e) => {
  // 历史任务卡片展开/收起（与运行日志样式一致）
  const histToggle = e.target.closest("[data-action='toggle-history']");
  if (histToggle) {
    const taskId = histToggle.dataset.task;
    const card = histToggle.closest(".history-card");
    if (card) {
      const collapsed = card.classList.toggle("collapsed");
      state.historyCollapsed[taskId] = !collapsed;
      const caret = card.querySelector(".log-caret");
      if (caret) caret.textContent = collapsed ? "▸" : "▾";
    }
    return;
  }

  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const action = btn.dataset.action;

  if (action === "stop") {
    const taskId = btn.dataset.task;
    try {
      await api(`/api/tasks/${taskId}/stop`, { method: "POST" });
      await loadSnapshot();
    } catch (err) {
      alert(err.message);
    }
    return;
  }

  if (action === "select-all" || action === "select-none") {
    const target = btn.dataset.target;
    const checked = action === "select-all";
    if (target === "regions") {
      state.selectedRegions = checked ? new Set(Object.keys(state.regions)) : new Set();
      saveConfig();
      renderRegions();
    } else if (target === "resources") {
      state.selectedResources = checked ? new Set(state.resources) : new Set();
      saveConfig();
      renderResources();
    } else if (target === "projects") {
      state.selectedProjects = checked ? new Set(state.projects.map((p) => p.project_id)) : new Set();
      saveConfig();
      renderProjects();
    }
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
  if (taskId !== state.currentLogTaskId) return;
  const pane = $("#log-panel");
  if (!pane) return;
  const div = document.createElement("div");
  div.className = `line ${item.level || "INFO"}`;
  const ts = new Date((item.ts || 0) * 1000).toLocaleTimeString();
  div.textContent = `${ts} [${item.level}] ${item.line}`;
  pane.appendChild(div);
  state.logCount += 1;
  updateLogBadge();
  const auto = $("#autoscroll");
  if (auto && auto.checked) pane.scrollTop = pane.scrollHeight;
}

// ---------- 表单 ----------
function bindForm() {
  $("#env-select").value = state.config.env;
  $("#public-key").value = state.config.public_key;

  $("#env-select").addEventListener("change", async (e) => {
    state.config.env = e.target.value;
    state.selectedRegions = new Set();
    state.projects = [];
    state.selectedProjects = new Set();
    renderProjects();
    $("#projects-msg").textContent = "";
    saveConfig();
    await loadRegions();
  });
  $("#public-key").addEventListener("input", (e) => { state.config.public_key = e.target.value; saveConfig(); });
  $("#private-key").addEventListener("input", (e) => { state.config.private_key = e.target.value; /* 不存 */ });
  $("#fetch-projects").addEventListener("click", fetchProjects);

  $("#submit-btn").addEventListener("click", onSubmit);
}

async function onSubmit() {
  const err = $("#submit-error"); err.textContent = "";
  const payload = {
    env_name: state.config.env === "test" ? "测试环境" : "正式环境",
    public_key: state.config.public_key.trim(),
    private_key: state.config.private_key,
    project_ids: [...state.selectedProjects],
    selected_regions: [...state.selectedRegions],
    selected_resources: [...state.selectedResources],
  };
  if (!payload.public_key) return err.textContent = "请填公钥";
  if (!payload.private_key) return err.textContent = "请填私钥";
  if (!payload.project_ids.length) return err.textContent = "请至少选择 1 个项目";
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
