"use strict";

const state = {
  config: { env: "prod", public_key: "", private_key: "", project_ids: "", api_url: "" },
  regions: {},
  resources: [],
  selectedRegions: new Set(),
  selectedResources: new Set(),
  tasks: { running: null, pending: [], history: [] },
  subscriptions: {},
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
  // 占位：完整实现在 Task 15
  const pendCount = (state.tasks.pending || []).length;
  $("#pending-count").textContent = `(${pendCount})`;
  $("#queue-badge").textContent = `队列: ${pendCount + (state.tasks.running ? 1 : 0)}`;
  $("#history-count").textContent = `(${(state.tasks.history || []).length})`;
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
  // 前端粗校验
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
    console.log("submitted:", res);
    // TODO Task 15: 订阅 SSE
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
}

main();
