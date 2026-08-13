"use strict";

const state = {
  capabilities: null,
  runs: [],
  selectedRun: null,
  summary: null,
  traces: [],
  events: [],
  files: [],
  traceOffset: 0,
  eventOffset: 0,
  polling: null,
  tab: "overview",
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload.error || payload || `HTTP ${response.status}`);
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pretty(value) {
  if (typeof value === "string") return value;
  return JSON.stringify(value ?? {}, null, 2);
}

function shortTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString("zh-CN", { hour12: false });
}

function bytes(value) {
  const n = Number(value || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
  return `${(n / 1024 / 1024).toFixed(1)} MiB`;
}

async function loadCapabilities() {
  try {
    state.capabilities = await api("/api/capabilities");
    const runtime = state.capabilities.runtime;
    $("runtimeLabel").textContent = `${runtime.model} · ${runtime.backend_profile}`;
    $("canList").innerHTML = state.capabilities.can.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    $("cannotList").innerHTML = state.capabilities.cannot.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  } catch (error) {
    $("runtimeLabel").textContent = error.message;
  }
}

async function checkHealth() {
  const button = $("healthButton");
  const dot = $("runtimeDot");
  button.disabled = true;
  $("runtimeLabel").textContent = "正在检查 RWKV endpoint…";
  dot.className = "status-dot unknown";
  try {
    const health = await api("/api/runtime/health");
    dot.className = `status-dot ${health.available ? "online" : "offline"}`;
    $("runtimeLabel").textContent = health.available
      ? `${health.model} · ${Math.round(health.latency_ms)} ms`
      : `离线 · ${health.error}`;
  } catch (error) {
    dot.className = "status-dot offline";
    $("runtimeLabel").textContent = `连接检查失败 · ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function addSeedFile(path = "", content = "") {
  const fragment = $("seedTemplate").content.cloneNode(true);
  fragment.querySelector(".seed-path").value = path;
  fragment.querySelector(".seed-content").value = content;
  fragment.querySelector(".remove-seed").addEventListener("click", (event) => {
    event.currentTarget.closest(".seed-file").remove();
  });
  $("seedFiles").appendChild(fragment);
}

function resetForm() {
  $("runForm").reset();
  $("maxTransitions").value = 200;
  $("seedFiles").innerHTML = "";
  $("formMessage").textContent = "";
  $("requestInput").focus();
}

function collectSeedFiles() {
  return [...document.querySelectorAll(".seed-file")]
    .map((row) => ({
      path: row.querySelector(".seed-path").value.trim(),
      content: row.querySelector(".seed-content").value,
    }))
    .filter((item) => item.path || item.content);
}

async function submitRun(event) {
  event.preventDefault();
  const button = $("startButton");
  button.disabled = true;
  $("formMessage").textContent = "正在创建隔离工作区…";
  try {
    const payload = {
      request: $("requestInput").value,
      constraints: $("constraintInput").value.split("\n").map((item) => item.trim()).filter(Boolean),
      max_transitions: Number($("maxTransitions").value),
      seed_files: collectSeedFiles(),
    };
    const result = await api("/api/runs", { method: "POST", body: JSON.stringify(payload) });
    $("formMessage").textContent = `已启动 ${result.run.run_id}`;
    await loadRuns();
    await selectRun(result.run.run_id);
  } catch (error) {
    $("formMessage").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function loadRuns() {
  try {
    const response = await api("/api/runs");
    state.runs = response.runs || [];
    $("runCount").textContent = state.runs.length;
    renderRunList();
  } catch (error) {
    $("runList").innerHTML = `<p class="muted-copy">${escapeHtml(error.message)}</p>`;
  }
}

function renderRunList() {
  if (!state.runs.length) {
    $("runList").innerHTML = '<p class="muted-copy">还没有手工测试记录。</p>';
    return;
  }
  $("runList").innerHTML = state.runs.map((run) => `
    <button class="run-item ${run.run_id === state.selectedRun ? "active" : ""}" data-run-id="${escapeHtml(run.run_id)}" type="button">
      <div><strong>${escapeHtml(run.run_id)}</strong><span>${escapeHtml(run.status || run.phase || "queued")}</span></div>
      <p>${escapeHtml(run.objective || run.request_preview || "正在建立目标")}</p>
    </button>`).join("");
  document.querySelectorAll(".run-item").forEach((button) => {
    button.addEventListener("click", () => selectRun(button.dataset.runId));
  });
}

async function selectRun(runId) {
  state.selectedRun = runId;
  state.summary = null;
  state.traces = [];
  state.events = [];
  state.files = [];
  state.traceOffset = 0;
  state.eventOffset = 0;
  $("emptyState").classList.add("hidden");
  $("runView").classList.remove("hidden");
  renderRunList();
  $("runId").textContent = runId;
  $("runObjective").textContent = "正在读取持久状态…";
  $("traceList").innerHTML = "";
  $("eventList").innerHTML = "";
  $("fileList").innerHTML = "";
  clearInterval(state.polling);
  await pollSelectedRun();
  state.polling = setInterval(pollSelectedRun, 1600);
}

async function pollSelectedRun() {
  const runId = state.selectedRun;
  if (!runId) return;
  try {
    const [summary, trace, events, files] = await Promise.all([
      api(`/api/runs/${encodeURIComponent(runId)}`),
      api(`/api/runs/${encodeURIComponent(runId)}/trace?after=${state.traceOffset}&limit=500`),
      api(`/api/runs/${encodeURIComponent(runId)}/events?after=${state.eventOffset}&limit=800`),
      api(`/api/runs/${encodeURIComponent(runId)}/files`),
    ]);
    if (state.selectedRun !== runId) return;
    state.summary = summary;
    state.traces.push(...(trace.events || []));
    state.traceOffset = trace.next_offset || state.traceOffset;
    state.events.push(...(events.events || []));
    state.eventOffset = events.last_event_id || state.eventOffset;
    state.files = files.files || [];
    renderSummary();
    renderTrace();
    renderEvents();
    renderFiles();
    const phase = summary.metadata.phase;
    if (["finished", "failed", "stopped"].includes(phase)) {
      clearInterval(state.polling);
      await loadRuns();
    }
  } catch (error) {
    $("errorPanel").classList.remove("hidden");
    $("errorOutput").textContent = error.message;
  }
}

function renderSummary() {
  const summary = state.summary;
  const metadata = summary.metadata || {};
  const runState = summary.state || {};
  const status = runState.status || metadata.status || metadata.phase || "queued";
  $("runId").textContent = metadata.run_id;
  $("runObjective").textContent = runState.objective || metadata.objective || summary.request.request;
  $("runStatus").textContent = status;
  $("runStatus").className = `status-pill ${status}`;
  $("revisionMetric").textContent = runState.revision ?? "—";
  $("requestMetric").textContent = runState.model_request_count ?? state.traces.filter((item) => item.type === "model_request_started").length;
  $("taskMetric").textContent = (runState.tasks || []).length;
  $("evidenceMetric").textContent = runState.criterion_evidence_count ?? 0;
  $("goalDigest").textContent = runState.goal_digest || "尚未创建";
  $("exportButton").href = `/api/runs/${encodeURIComponent(metadata.run_id)}/export`;
  $("stopButton").classList.toggle("hidden", !metadata.active);
  const canResume = !metadata.active && (status === "interrupted" || metadata.phase === "stopped" || metadata.phase === "failed") && metadata.state_created;
  $("resumeButton").classList.toggle("hidden", !canResume);

  const criteria = runState.criteria || [];
  $("criteriaList").innerHTML = criteria.length ? criteria.map((item) => `
    <div class="criterion"><strong>${escapeHtml(item.criterion_id)} · ${item.required ? "required" : "optional"}</strong><p>${escapeHtml(item.description)}</p></div>`).join("") : '<p class="muted-copy">等待 RWKV 解析目标。</p>';

  const tasks = runState.tasks || [];
  $("taskSummary").textContent = `${tasks.length} tasks`;
  $("taskList").innerHTML = tasks.length ? tasks.map((task) => `
    <div class="task ${escapeHtml(task.status)}"><strong>${escapeHtml(task.task_id)} · ${escapeHtml(task.title)}</strong><p>${escapeHtml(task.status)} · attempts ${task.attempts} · deps ${task.dependencies.join(", ") || "none"}</p></div>`).join("") : '<p class="muted-copy">尚无任务。</p>';

  const finalOutput = summary.result?.final_output ?? runState.final_output ?? "";
  $("finalOutput").textContent = finalOutput || "运行尚未产生最终输出。";
  const errors = [metadata.error, ...(runState.errors || []).map((item) => pretty(item))].filter(Boolean);
  $("errorPanel").classList.toggle("hidden", errors.length === 0);
  $("errorOutput").textContent = errors.join("\n\n");
  $("traceCount").textContent = state.traces.length;
  $("eventCount").textContent = state.events.length;
  $("fileCount").textContent = state.files.length;
}

function traceHeadline(item) {
  if (item.type === "model_request_started") return item.request_type || "RWKV prompt";
  if (item.type === "model_request_returned") return `${item.request_type || "RWKV"} · finish=${item.finish_reason || "unknown"}`;
  if (item.type === "model_protocol_normalized") return item.normalization || "protocol transformation";
  return item.error || item.request_type || item.type;
}

function traceBody(item) {
  const parts = [];
  const fields = [
    ["完整 Prompt", item.prompt],
    ["RWKV Raw Output", item.raw_output],
    ["可见文本投影", item.normalized_visible_output],
    ["归一化前 Payload", item.input_payload],
    ["归一化后 Payload", item.normalized_payload],
    ["Parsed Payload", item.parsed_payload],
    ["错误", item.error],
  ];
  for (const [label, value] of fields) {
    if (value !== undefined && value !== null && value !== "") {
      parts.push(`<h4>${label}</h4><pre>${escapeHtml(pretty(value))}</pre>`);
    }
  }
  const meta = Object.fromEntries(Object.entries(item).filter(([key]) => !["prompt", "raw_output", "normalized_visible_output", "output", "input_payload", "normalized_payload", "parsed_payload"].includes(key)));
  parts.push(`<h4>事件元数据</h4><pre>${escapeHtml(pretty(meta))}</pre>`);
  return parts.join("");
}

function renderTrace() {
  const filter = $("traceFilter").value;
  const rows = state.traces.filter((item) => filter === "all" || item.type === filter);
  $("traceList").innerHTML = rows.length ? rows.map((item, index) => `
    <details class="trace-event" ${index === rows.length - 1 ? "open" : ""}>
      <summary><span class="trace-type">${escapeHtml(item.type)}</span><span class="trace-title">${escapeHtml(traceHeadline(item))}</span></summary>
      <div class="trace-body">${traceBody(item)}</div>
    </details>`).join("") : '<p class="muted-copy">还没有匹配的模型事件。</p>';
}

function renderEvents() {
  $("eventList").innerHTML = state.events.length ? state.events.map((item) => `
    <article class="event-card"><time>${escapeHtml(shortTime(item.timestamp))}<br>rev ${item.revision}</time><strong>${escapeHtml(item.type)}</strong><pre>${escapeHtml(pretty(item.data))}</pre></article>`).join("") : '<p class="muted-copy">Goal 创建后，Controller 事件会显示在这里。</p>';
}

function renderFiles() {
  $("fileCount").textContent = state.files.length;
  $("fileList").innerHTML = state.files.length ? state.files.map((item) => `
    <button class="file-item" data-file-path="${escapeHtml(item.path)}" type="button"><strong>${escapeHtml(item.path)}</strong><span>${bytes(item.size_bytes)} · ${escapeHtml(item.sha256.slice(0, 12))}</span></button>`).join("") : '<p class="muted-copy">工作区为空。</p>';
  document.querySelectorAll(".file-item").forEach((button) => {
    button.addEventListener("click", () => previewFile(button.dataset.filePath, button));
  });
}

async function previewFile(path, button) {
  document.querySelectorAll(".file-item").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const metadata = state.files.find((item) => item.path === path);
  $("filePreviewName").textContent = path;
  $("filePreviewMeta").textContent = metadata ? `${bytes(metadata.size_bytes)} · ${metadata.media_type}` : "";
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(state.selectedRun)}/file/${path.split("/").map(encodeURIComponent).join("/")}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = response.headers.get("content-type") || "";
    if (type.startsWith("text/") || type.includes("json") || type.includes("javascript") || type.includes("xml")) {
      $("filePreview").textContent = await response.text();
    } else {
      $("filePreview").textContent = `二进制文件（${type}），请使用浏览器打开或从审计包下载。`;
    }
  } catch (error) {
    $("filePreview").textContent = error.message;
  }
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  $(`${tab}Tab`).classList.add("active");
}

async function runAction(action) {
  if (!state.selectedRun) return;
  try {
    await api(`/api/runs/${encodeURIComponent(state.selectedRun)}/${action}`, { method: "POST", body: "{}" });
    await pollSelectedRun();
    if (!state.polling) state.polling = setInterval(pollSelectedRun, 1600);
  } catch (error) {
    $("errorPanel").classList.remove("hidden");
    $("errorOutput").textContent = error.message;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("healthButton").addEventListener("click", checkHealth);
  $("newRunButton").addEventListener("click", resetForm);
  $("addSeedButton").addEventListener("click", () => addSeedFile());
  $("runForm").addEventListener("submit", submitRun);
  $("traceFilter").addEventListener("change", renderTrace);
  $("stopButton").addEventListener("click", () => runAction("stop"));
  $("resumeButton").addEventListener("click", () => runAction("resume"));
  document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  await Promise.all([loadCapabilities(), loadRuns()]);
});
