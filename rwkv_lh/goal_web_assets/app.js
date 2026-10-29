"use strict";

const app = {
  runs: [],
  selectedRun: "",
  summary: null,
  events: [],
  traces: [],
  files: [],
  eventOffset: 0,
  traceOffset: 0,
  topology: null,
  polling: null,
  selectionVersion: 0,
  pollFlight: null,
  activeTab: "overview",
  auditMode: "trace",
  selectedFile: "",
  previewRequest: 0,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload?.error || payload || `HTTP ${response.status}`);
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
  return typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2);
}

function time(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleTimeString("zh-CN", { hour12: false });
}

function bytes(value) {
  const size = Number(value || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 ** 2) return `${(size / 1024).toFixed(1)} KiB`;
  return `${(size / 1024 ** 2).toFixed(1)} MiB`;
}

function statusClass(value) {
  return String(value || "queued").toLowerCase().replaceAll("_", "-");
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

function seedFiles() {
  return [...document.querySelectorAll(".seed-file")]
    .map((row) => ({
      path: row.querySelector(".seed-path").value.trim(),
      content: row.querySelector(".seed-content").value,
    }))
    .filter((item) => item.path || item.content);
}

async function loadTopology() {
  const dot = $("systemDot");
  dot.className = "live-dot pending";
  try {
    app.topology = await api("/api/runtime/topology");
    const healthy = Boolean(
      app.topology.executor?.available
      && app.topology.harness?.available
    );
    dot.className = `live-dot ${healthy ? "" : "offline"}`;
    $("systemLabel").textContent = healthy ? "RWKV 服务可用" : "部分运行服务不可用";
    renderTopology();
  } catch (error) {
    dot.className = "live-dot offline";
    $("systemLabel").textContent = `运行栈检查失败`;
    $("topologyCards").innerHTML = `<article class="offline"><span class="node-index">!</span><strong>无法读取拓扑</strong><p>${escapeHtml(error.message)}</p></article>`;
  }
}

function renderTopology() {
  if (!app.topology) return;
  const topology = app.topology;
  const cards = [
    { index: "01", name: "计划模型", ok: null, detail: '循环派单 · 接收宿主事实报告' },
    { index: "02", name: "RWKV Executor", ok: topology.executor?.available, detail: `${topology.executor?.model || "RWKV"} · 持续执行、自测与交回` },
    { index: "03", name: "工具与事实报告", ok: topology.harness?.available, detail: '隔离工作区 · 实际结果与变更' },
  ];
  $("topologyCards").innerHTML = cards.map((card) => `
    <article class="${card.ok === null ? 'pending' : card.ok ? "online" : "offline"}">
      <span class="node-index">${card.index}</span><strong>${escapeHtml(card.name)}</strong><p>${escapeHtml(card.detail)}</p>
    </article>`).join("");
  $("topologyDetail").innerHTML = cards.map((card) => `
    <div class="topology-row"><span>${escapeHtml(card.name)}</span><strong>${escapeHtml(card.detail)}</strong><code>${card.ok === null ? '未检查连接' : card.ok ? "READY" : "UNAVAILABLE"}</code></div>`).join("")
    + `<details class="raw-event"><summary><code>IDENTITY</code><strong>完整运行身份</strong></summary><pre>${escapeHtml(pretty(topology))}</pre></details>`;
}

async function loadRuns() {
  try {
    const result = await api("/api/runs");
    app.runs = result.runs || [];
    $("runCount").textContent = app.runs.length;
    renderRuns();
  } catch (error) {
    $("runList").innerHTML = `<p class="empty-copy">${escapeHtml(error.message)}</p>`;
  }
}

function renderRuns() {
  if (!app.runs.length) {
    $("runList").innerHTML = '<p class="empty-copy">还没有项目记录。</p>';
    return;
  }
  $("runList").innerHTML = app.runs.map((run) => {
    const status = statusClass(run.status || run.phase);
    return `<button class="run-item ${run.run_id === app.selectedRun ? "active" : ""}" data-run-id="${escapeHtml(run.run_id)}" type="button">
      <div><strong>${escapeHtml(run.run_id)}</strong><span class="${status}"></span></div><p>${escapeHtml(run.request_preview || "正在建立目标")}</p>
    </button>`;
  }).join("");
  document.querySelectorAll(".run-item").forEach((button) => button.addEventListener("click", () => selectRun(button.dataset.runId)));
}

async function submitGoal(event) {
  event.preventDefault();
  const start = $("startButton");
  start.disabled = true;
  $("formMessage").textContent = "正在创建不可变 Goal 与隔离工作区…";
  try {
    const payload = {
      request: $("goalInput").value.trim(),
      constraints: $("constraintInput").value.split("\n").map((item) => item.trim()).filter(Boolean),
      max_transitions: Number($("transitionBudget").value),
      max_seconds: Number($("secondsBudget").value),
      tool_scope: $("toolScope").value,
      seed_files: seedFiles(),
    };
    const result = await api("/api/runs", { method: "POST", body: JSON.stringify(payload) });
    $("formMessage").textContent = `Goal 已启动：${result.run.run_id}`;
    await loadRuns();
    await selectRun(result.run.run_id);
  } catch (error) {
    $("formMessage").textContent = error.message;
  } finally {
    start.disabled = false;
  }
}

function resetFilePreview() {
  app.previewRequest += 1;
  app.selectedFile = "";
  $("filePreviewName").textContent = "选择文件预览";
  $("filePreviewMeta").textContent = "";
  $("filePreview").textContent = "";
  $("filePreview").setAttribute("aria-busy", "false");
}

function newGoal() {
  resetFilePreview();
  clearInterval(app.polling);
  app.polling = null;
  app.selectionVersion += 1;
  app.pollFlight = null;
  app.selectedRun = "";
  app.summary = null;
  $("runView").classList.add("hidden");
  $("createView").classList.remove("hidden");
  $("goalInput").focus();
  renderRuns();
}

async function selectRun(runId) {
  resetFilePreview();
  clearInterval(app.polling);
  app.polling = null;
  const version = ++app.selectionVersion;
  app.pollFlight = null;
  app.selectedRun = runId;
  app.summary = null;
  app.events = [];
  app.traces = [];
  app.files = [];
  app.eventOffset = 0;
  app.traceOffset = 0;
  $("createView").classList.add("hidden");
  $("runView").classList.remove("hidden");
  $("runId").textContent = runId;
  $("runObjective").textContent = "正在恢复持久状态…";
  // Clear every task projection before fetching the new identity. Otherwise
  // a slow response temporarily labels the previous answer as this task's.
  renderRun();
  renderRuns();
  await pollRun();
  if (version !== app.selectionVersion || runId !== app.selectedRun) return;
  const phase = app.summary?.metadata?.phase;
  if (!["finished", "failed", "stopped", "blocked"].includes(phase)) {
    app.polling = setInterval(pollRun, 1700);
  }
}

async function pollRun() {
  const runId = app.selectedRun;
  const version = app.selectionVersion;
  if (!runId) return;
  const isCurrent = () => runId === app.selectedRun && version === app.selectionVersion;
  if (app.pollFlight?.runId === runId && app.pollFlight.version === version) {
    return app.pollFlight.promise;
  }
  const flight = { runId, version };
  app.pollFlight = flight;
  flight.promise = (async () => {
    try {
      // Keep ownership until every sibling request settles, even on failure.
      // Otherwise an early rejection lets the next tick overlap slow requests.
      const results = await Promise.allSettled([
        api(`/api/runs/${encodeURIComponent(runId)}`),
        api(`/api/runs/${encodeURIComponent(runId)}/events?after=${app.eventOffset}&limit=1200`),
        api(`/api/runs/${encodeURIComponent(runId)}/trace?after=${app.traceOffset}&limit=800`),
        api(`/api/runs/${encodeURIComponent(runId)}/files`),
      ]);
      if (!isCurrent()) return;
      const failure = results.find((result) => result.status === "rejected");
      if (failure) throw failure.reason;
      const [summary, events, traces, files] = results.map((result) => result.value);
      app.summary = summary;
      app.events.push(...(events.events || []));
      app.eventOffset = Math.max(app.eventOffset, events.last_event_id || 0);
      app.traces.push(...(traces.events || []));
      app.traceOffset = Math.max(app.traceOffset, traces.next_offset || 0);
      app.files = files.files || [];
      renderRun();
      const phase = summary.metadata?.phase;
      if (["finished", "failed", "stopped", "blocked"].includes(phase)) {
        clearInterval(app.polling);
        app.polling = null;
        await loadRuns();
      }
    } catch (error) {
      if (!isCurrent()) return;
      $("errorPanel").classList.remove("hidden");
      $("errorOutput").textContent = error.message;
    } finally {
      if (app.pollFlight === flight) app.pollFlight = null;
    }
  })();
  return flight.promise;
}

function renderRun() {
  const summary = app.summary || {};
  const metadata = summary.metadata || {};
  const project = summary.project;
  const status = statusClass(metadata.active ? (project?.status || metadata.status || metadata.phase)
    : (summary.result?.status || project?.status || metadata.status || metadata.phase));
  const orders = project?.work_orders || [];
  const actions = project?.actions || [];
  $("runId").textContent = metadata.run_id || app.selectedRun;
  $("runObjective").textContent = summary.request?.request || "—";
  $("runStatus").textContent = status;
  $("runStatus").className = `status-chip ${status}`;
  $("exportButton").href = `/api/runs/${encodeURIComponent(app.selectedRun)}/export`;
  const resumable = summary.request?.tool_scope === 'coding' && !metadata.active && metadata.state_created
    && ["interrupted", "stopped", "failed", "blocked"].includes(status);
  $("resumeButton").classList.toggle("hidden", !resumable);
  $("obligationMetric").textContent = `${orders.filter(item => item.report !== null).length} / ${orders.length}`;
  $("actionMetric").textContent = actions.length;
  $("evidenceMetric").textContent = actions.length;
  $("fileMetric").textContent = app.files.length;
  $("requestMetric").textContent = project?.calls ?? summary.result?.generation_started ?? 0;
  $("contractCount").textContent = orders.length;
  $("executionCount").textContent = actions.length;
  $("evidenceCount").textContent = actions.length;
  $("artifactCount").textContent = app.files.length;
  $("rawCount").textContent = app.traces.length + app.events.length;
  $("currentPhaseLabel").textContent = status === 'finished' ? '模型已结束（未验收）'
    : status === 'blocked' ? '模型报告阻塞' : status === 'failed' ? '执行失败'
    : status === 'interrupted' ? '运行已中断' : project?.current_order ? 'RWKV 正在执行工单' : '等待计划模型派单';
  renderOverview(summary);
  renderContract(summary);
  renderActions(actions);
  renderEvidence(project);
  renderFiles();
  renderRaw();
}

function eventHeadline(item) {
  const data = item.data || {};
  return data.operation || data.work_order_id || data.reason || item.kind || item.type;
}

function renderOverview(summary) {
  const recent = app.events.slice(-10).reverse();
  $("liveActivity").innerHTML = recent.length ? recent.map((item) => `
    <div class="activity-item"><i></i><time>${escapeHtml(time(item.timestamp))}</time><strong>${escapeHtml(eventHeadline(item))}</strong></div>`).join("") : '<p class="empty-copy">等待第一条运行记录。</p>';
  const output = summary.project?.final ?? summary.result?.final_output ?? "";
  $("finalOutput").textContent = !summary.metadata ? "正在加载任务记录…" : output || (summary.metadata?.active ? "项目执行中，尚无结束声明。" : "本次运行未提交结束声明。");
  $("acceptanceBadge").textContent = '模型声明与工具事实分开记录；未做验收';
  $("acceptanceBadge").className = 'review-badge pending';
  const errors = [summary.metadata?.error].filter(Boolean);
  $("errorPanel").classList.toggle("hidden", !errors.length);
  $("errorOutput").textContent = errors.join("\n\n");
}

function renderContract(summary) {
  const project = summary.project;
  const orders = project?.work_orders || [];
  $("goalDigest").textContent = project?.current_order?.id || (orders.length ? '已交回当前工单' : '等待首张工单');
  $("goalRequest").textContent = summary.request?.request || '—';
  $("obligationBoard").innerHTML = project ? `<article class="obligation"><header><code>${escapeHtml(project.goal.id)}</code></header><p>${escapeHtml(project.goal.request)}</p></article>` : '<p class="empty-copy">等待创建项目记录。</p>';
  $("nodeCount").textContent = `${orders.length} orders`;
  $("graphNodes").innerHTML = orders.map(item => {
    const order = item.order, report = item.report;
    const label = project.current_order?.id === order.id ? '当前工单' : report ? '已交回（未验收）' : '已派发';
    return `<article class="graph-node"><header><code>${escapeHtml(order.id)}</code><span>${label}</span></header>
      <strong>${escapeHtml(order.goal)}</strong><p>可写范围：${escapeHtml(order.scope.join(', ') || '只读')}</p>
      <p>检查命令：${escapeHtml(order.checks.join(' · ') || '无')}</p>
      <p>模型调用：${report ? report.calls_used : '待交回'} / ${order.call_budget}</p>
      ${report ? `<details><summary>宿主事实报告</summary><pre>${escapeHtml(pretty(report))}</pre></details>` : ''}</article>`;
  }).join('') || '<p class="empty-copy">计划模型尚未派发工单。</p>';
}

function renderActions(actions) {
  $("actionList").innerHTML = actions.map((action, index) => `
    <article class="action-card ${escapeHtml(statusClass(action.status))}">
      <span class="sequence">${String(index + 1).padStart(2, "0")}</span>
      <code>${escapeHtml(action.operation)}</code>
      <p>${escapeHtml(action.work_order_id || '')} · ${escapeHtml(action.action_id)}</p>
      <span class="action-status">${escapeHtml(action.status)}</span>
      <details><summary>真实调用与工具结果</summary><pre>${escapeHtml(pretty({arguments: action.arguments, result: action.result}))}</pre></details>
    </article>`).join('') || '<p class="empty-copy">等待第一条工具回执。</p>';
}

function renderEvidence(project) {
  const actions = project?.actions || [];
  const reports = (project?.work_orders || []).filter(item => item.report !== null);
  $("reviewSummary").textContent = `工具回执 ${actions.length} 条，工单报告 ${reports.length} 份；结束声明不代表验收通过。`;
  $("evidenceTimeline").innerHTML = reports.map(item =>
    `<article class="evidence-card"><strong>工单 ${escapeHtml(item.order.id)} 的宿主事实报告</strong><pre>${escapeHtml(pretty(item.report))}</pre></article>`).join('') +
    actions.map(action => `<article class="evidence-card"><strong>实际工具回执</strong><pre>${escapeHtml(pretty(action))}</pre></article>`).join('') +
    (project?.final_claim ? `<article class="evidence-card"><strong>项目结束声明</strong><pre>${escapeHtml(pretty(project.final_claim))}</pre></article>` : '');
}

function renderFiles() {
  $("fileList").innerHTML = app.files.length ? app.files.map((item) => `
    <button class="file-item ${item.path === app.selectedFile ? "active" : ""}" data-file-path="${escapeHtml(item.path)}" type="button"><strong>${escapeHtml(item.path)}</strong><span>${bytes(item.size_bytes)} · ${escapeHtml(item.sha256.slice(0, 12))}</span></button>`).join("") : '<p class="empty-copy">工作区尚无文件。</p>';
  document.querySelectorAll(".file-item").forEach((button) => button.addEventListener("click", () => previewFile(button.dataset.filePath, button)));
}

async function previewFile(path, button) {
  const runId = app.selectedRun;
  const requestId = ++app.previewRequest;
  app.selectedFile = path;
  const isCurrent = () => requestId === app.previewRequest
    && runId === app.selectedRun && path === app.selectedFile;
  document.querySelectorAll(".file-item").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const metadata = app.files.find((item) => item.path === path);
  $("filePreviewName").textContent = path;
  $("filePreviewMeta").textContent = metadata ? `${bytes(metadata.size_bytes)} · ${metadata.media_type}` : "";
  $("filePreview").textContent = "正在加载…";
  $("filePreview").setAttribute("aria-busy", "true");
  try {
    const encoded = path.split("/").map(encodeURIComponent).join("/");
    const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/file/${encoded}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = response.headers.get("content-type") || "";
    const content = type.startsWith("text/") || /json|javascript|xml/.test(type)
      ? await response.text()
      : `二进制文件（${type}），请从审计包下载。`;
    // The body can arrive after headers and after another file or run is chosen.
    if (isCurrent()) $("filePreview").textContent = content;
  } catch (error) {
    if (isCurrent()) $("filePreview").textContent = error.message;
  } finally {
    if (isCurrent()) $("filePreview").setAttribute("aria-busy", "false");
  }
}

function traceHeadline(item) {
  return item.request_type || item.error || item.finish_reason || item.type || "model event";
}

function renderRaw() {
  const rows = app.auditMode === "trace" ? app.traces : app.events;
  $("rawTimeline").innerHTML = rows.length ? rows.slice().reverse().map((item) => `
    <details class="raw-event"><summary><code>${escapeHtml(item.type || "event")}</code><strong>${escapeHtml(app.auditMode === "trace" ? traceHeadline(item) : eventHeadline(item))}</strong></summary><pre>${escapeHtml(pretty(item))}</pre></details>`).join("") : '<p class="empty-copy">等待审计记录。</p>';
}

function switchTab(tab) {
  app.activeTab = tab;
  document.querySelectorAll(".run-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  $(`${tab}Tab`).classList.add("active");
}

async function runAction(action) {
  if (!app.selectedRun) return;
  try {
    await api(`/api/runs/${encodeURIComponent(app.selectedRun)}/${action}`, { method: "POST", body: "{}" });
    await pollRun();
    if (!app.polling) app.polling = setInterval(pollRun, 1700);
  } catch (error) {
    $("errorPanel").classList.remove("hidden");
    $("errorOutput").textContent = error.message;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("goalForm").addEventListener("submit", submitGoal);
  $("newGoalButton").addEventListener("click", newGoal);
  $("addSeedButton").addEventListener("click", () => addSeedFile());
  $("resumeButton").addEventListener("click", () => runAction("resume"));
  $("topologyButton").addEventListener("click", () => $("topologyDialog").showModal());
  $("closeTopologyButton").addEventListener("click", () => $("topologyDialog").close());
  document.querySelectorAll("[data-goal]").forEach((button) => button.addEventListener("click", () => {
    $("goalInput").value = button.dataset.goal;
    $("goalInput").focus();
  }));
  document.querySelectorAll(".run-tabs button").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  document.querySelectorAll("[data-audit]").forEach((button) => button.addEventListener("click", () => {
    app.auditMode = button.dataset.audit;
    document.querySelectorAll("[data-audit]").forEach((item) => item.classList.toggle("active", item === button));
    renderRaw();
  }));
  await Promise.all([loadTopology(), loadRuns(), loadDemos()]);
});

async function loadDemos() {
  try {
    const { demos } = await api("/api/demos");
    $("demoButtons").replaceChildren();
    demos.forEach((demo) => {
      const button = document.createElement("button");
      button.type = "button"; button.textContent = demo.title; button.dataset.demo = demo.id;
      button.addEventListener("click", () => {
        $("goalInput").value = demo.request;
        $("toolScope").value = demo.tool_scope;
        $("transitionBudget").value = demo.max_transitions;
        $("secondsBudget").value = demo.max_seconds;
        $("constraintInput").value = "";
        $("seedFiles").replaceChildren();
        demo.seed_files.forEach((file) => addSeedFile(file.path, file.content));
        $("formMessage").textContent = "已填入任务和原始文件。点击开始执行会发起新的真实模型调用。";
      });
      $("demoButtons").appendChild(button);
    });
  } catch (error) { $("formMessage").textContent = error.message; }
}
