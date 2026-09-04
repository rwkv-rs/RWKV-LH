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
  activeTab: "overview",
  auditMode: "trace",
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
      app.topology.supervisor?.configured
      && app.topology.selector?.available
      && app.topology.executor?.available
      && app.topology.harness?.available
    );
    dot.className = `live-dot ${healthy ? "" : "offline"}`;
    $("systemLabel").textContent = healthy ? "双 RWKV 运行栈已就绪" : "部分运行服务不可用";
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
    { index: "01", name: "Strong Planner", ok: topology.supervisor?.configured, detail: `${topology.supervisor?.model || "未配置"} · Contract Graph` },
    { index: "02", name: "RWKV Selector", ok: topology.selector?.available, detail: `${topology.selector?.model || "2.9B"} · ${topology.selector?.device || "GPU2"}` },
    { index: "03", name: "RWKV Executor", ok: topology.executor?.available, detail: `${topology.executor?.model || "13.3B"} · ${topology.executor?.device || "GPU1"}` },
    { index: "04", name: "Evidence Harness", ok: topology.harness?.available, detail: `${topology.harness?.scope || "isolated"} · append-only` },
  ];
  $("topologyCards").innerHTML = cards.map((card) => `
    <article class="${card.ok ? "online" : "offline"}">
      <span class="node-index">${card.index}</span><strong>${escapeHtml(card.name)}</strong><p>${escapeHtml(card.detail)}</p>
    </article>`).join("");
  $("topologyDetail").innerHTML = cards.map((card) => `
    <div class="topology-row"><span>${escapeHtml(card.name)}</span><strong>${escapeHtml(card.detail)}</strong><code>${card.ok ? "READY" : "UNAVAILABLE"}</code></div>`).join("")
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
      retrieval_policy: {
        mode: $("networkPolicy").value,
        explicit_approval: false,
        public_workspace_paths: [],
      },
      supervisor_mode: "stateful_goal",
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

function newGoal() {
  clearInterval(app.polling);
  app.polling = null;
  app.selectedRun = "";
  app.summary = null;
  $("runView").classList.add("hidden");
  $("createView").classList.remove("hidden");
  $("goalInput").focus();
  renderRuns();
}

async function selectRun(runId) {
  clearInterval(app.polling);
  app.polling = null;
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
  renderRuns();
  await pollRun();
  const phase = app.summary?.metadata?.phase;
  if (!["finished", "failed", "stopped", "blocked"].includes(phase)) {
    app.polling = setInterval(pollRun, 1700);
  }
}

async function pollRun() {
  const runId = app.selectedRun;
  if (!runId) return;
  try {
    const [summary, events, traces, files] = await Promise.all([
      api(`/api/runs/${encodeURIComponent(runId)}`),
      api(`/api/runs/${encodeURIComponent(runId)}/events?after=${app.eventOffset}&limit=1200`),
      api(`/api/runs/${encodeURIComponent(runId)}/trace?after=${app.traceOffset}&limit=800`),
      api(`/api/runs/${encodeURIComponent(runId)}/files`),
    ]);
    if (runId !== app.selectedRun) return;
    app.summary = summary;
    app.events.push(...(events.events || []));
    app.eventOffset = events.last_event_id || app.eventOffset;
    app.traces.push(...(traces.events || []));
    app.traceOffset = traces.next_offset || app.traceOffset;
    app.files = files.files || [];
    renderRun();
    const phase = summary.metadata?.phase;
    if (["finished", "failed", "stopped", "blocked"].includes(phase)) {
      clearInterval(app.polling);
      app.polling = null;
      await loadRuns();
    }
  } catch (error) {
    $("errorPanel").classList.remove("hidden");
    $("errorOutput").textContent = error.message;
  }
}

function contractData() {
  const patches = app.events.filter((item) => item.type === "goal_plan_patch_committed").map((item) => item.data?.patch || {});
  const activeSteps = new Map();
  const stagedSteps = (patch, field) => (patch[field] || []).flatMap((stage) =>
    (stage.steps || []).map((step) => ({ ...step, stage: stage.stage }))
  );
  patches.forEach((patch) => {
    (patch.discard_step_ids || []).forEach((stepId) => activeSteps.delete(stepId));
    [...(patch.replace_steps || []), ...stagedSteps(patch, "replace_stages")]
      .forEach((step) => activeSteps.set(step.step_id, step));
    [...(patch.add_steps || []), ...stagedSteps(patch, "add_stages")]
      .forEach((step) => activeSteps.set(step.step_id, step));
  });
  const reviews = app.events.filter((item) => item.type === "goal_audit_accepted").map((item) => item.data?.audit || {});
  const latestReview = reviews.at(-1) || {};
  const verdicts = {};
  reviews.forEach((audit) => {
    (audit.completed_steps || []).forEach((step) => {
      verdicts[step.step_id] = { obligation_id: step.step_id, status: "satisfied", evidence_refs: step.evidence_refs || [] };
    });
    if (audit.verdict === "repair" && audit.step_id) {
      verdicts[audit.step_id] = { obligation_id: audit.step_id, status: "insufficient", gaps: audit.gaps || [] };
    }
  });
  const steps = [...activeSteps.values()];
  const obligations = steps.map((step) => ({ obligation_id: step.step_id, predicate: step.objective }));
  const nodes = steps.map((step) => ({ node_id: step.step_id, atom: { ...step, atom_id: step.step_id } }));
  const outcomes = Object.fromEntries(steps.map((step) => [step.step_id, { status: verdicts[step.step_id]?.status || "pending" }]));
  return { patches, obligations, nodes, reviews, latestReview, verdicts, outcomes };
}

function currentPhase(contract, status) {
  if (status === "completed") return "complete";
  if (contract.reviews.length) return "verify";
  if (Object.keys(contract.outcomes).length || (app.summary?.state?.actions || []).length) return "build";
  if (contract.patches.length) return "plan";
  return "understand";
}

function renderRun() {
  const summary = app.summary || {};
  const metadata = summary.metadata || {};
  const state = summary.state || {};
  const status = statusClass(state.status || metadata.status || metadata.phase);
  const contract = contractData();
  const satisfied = Object.values(contract.verdicts).filter((item) => item.status === "satisfied").length;
  const current = currentPhase(contract, status);
  const actions = state.actions || [];
  const evidenceEvents = app.events.filter(isEvidenceEvent);

  $("runId").textContent = metadata.run_id || app.selectedRun;
  $("runObjective").textContent = state.request || summary.request?.request || "—";
  $("runStatus").textContent = status;
  $("runStatus").className = `status-chip ${status}`;
  $("runStatus").textContent = status;
  $("exportButton").href = `/api/runs/${encodeURIComponent(app.selectedRun)}/export`;
  const resumable = !metadata.active && metadata.state_created && ["interrupted", "stopped", "failed", "blocked"].includes(status);
  $("resumeButton").classList.toggle("hidden", !resumable);

  $("obligationMetric").textContent = `${satisfied} / ${contract.obligations.length}`;
  $("actionMetric").textContent = actions.length;
  $("evidenceMetric").textContent = evidenceEvents.length;
  $("fileMetric").textContent = app.files.length;
  $("requestMetric").textContent = state.model_request_count ?? app.traces.filter((item) => item.type === "model_request_started").length;
  $("contractCount").textContent = contract.obligations.length;
  $("executionCount").textContent = actions.length;
  $("evidenceCount").textContent = evidenceEvents.length;
  $("artifactCount").textContent = app.files.length;
  $("rawCount").textContent = app.traces.length + app.events.length;
  $("currentPhaseLabel").textContent = phaseLabel(current);

  renderPhases(current, status);
  renderOverview(summary, contract);
  renderContract(summary, contract);
  renderActions(actions);
  renderEvidence(contract, evidenceEvents);
  renderFiles();
  renderRaw();
}

function phaseLabel(phase) {
  return ({ understand: "正在理解目标", plan: "正在拆解计划", build: "RWKV 正在创建", verify: "正在审核证据", complete: "项目已交付" })[phase] || "运行中";
}

function renderPhases(current, status) {
  const order = ["understand", "plan", "build", "verify", "complete"];
  const index = order.indexOf(current);
  document.querySelectorAll(".phase-track [data-phase]").forEach((row) => {
    const rowIndex = order.indexOf(row.dataset.phase);
    row.classList.toggle("done", rowIndex < index || status === "completed");
    row.classList.toggle("active", rowIndex === index && status !== "completed");
  });
}

function eventHeadline(item) {
  const data = item.data || {};
  return data.operation || data.atom_id || data.stage_id || data.patch_id || data.review_id || data.reason || item.type;
}

function renderOverview(summary, contract) {
  const recent = app.events.slice(-10).reverse();
  $("liveActivity").innerHTML = recent.length ? recent.map((item) => `
    <div class="activity-item"><i></i><time>${escapeHtml(time(item.timestamp))}</time><strong>${escapeHtml(eventHeadline(item))}</strong></div>`).join("") : '<p class="empty-copy">等待第一个因果事件。</p>';
  const output = summary.result?.final_output ?? summary.state?.final_output ?? "";
  $("finalOutput").textContent = output || "项目仍在创建中。";
  const verdicts = Object.values(contract.verdicts);
  const allPassed = Boolean(contract.obligations.length) && verdicts.length >= contract.obligations.length && verdicts.every((item) => item.status === "satisfied");
  const contradicted = verdicts.some((item) => item.status === "contradicted");
  $("acceptanceBadge").textContent = allPassed ? "证据验收通过" : contradicted ? "发现矛盾" : "等待验收";
  $("acceptanceBadge").className = `review-badge ${allPassed ? "pass" : contradicted ? "fail" : "pending"}`;
  const errors = [summary.metadata?.error, ...(summary.state?.errors || []).map(pretty)].filter(Boolean);
  $("errorPanel").classList.toggle("hidden", !errors.length);
  $("errorOutput").textContent = errors.join("\n\n");
}

function renderContract(summary, contract) {
  $("goalDigest").textContent = summary.state?.goal_digest || "尚未创建";
  $("goalRequest").textContent = summary.state?.request || summary.request?.request || "—";
  $("obligationBoard").innerHTML = contract.obligations.length ? contract.obligations.map((item) => {
    const verdict = contract.verdicts[item.obligation_id] || {};
    const status = verdict.status || "open";
    return `<article class="obligation ${escapeHtml(status)}"><header><code>${escapeHtml(item.obligation_id)}</code><span>${escapeHtml(status)}</span></header><p>${escapeHtml(item.predicate || item.request_clause || "待解析义务")}</p></article>`;
  }).join("") : '<p class="empty-copy">Planner 尚未提交义务。</p>';
  $("nodeCount").textContent = `${contract.nodes.length} steps`;
  $("graphNodes").innerHTML = contract.nodes.length ? contract.nodes.map((node) => {
    const atom = node.atom || {};
    const outcome = contract.outcomes[atom.atom_id || node.node_id] || {};
    return `<article class="graph-node"><header><code>${escapeHtml(node.node_id || atom.atom_id)}</code><span>${escapeHtml(outcome.status || "pending")}</span></header><strong>${escapeHtml(atom.objective || "RWKV step")}</strong><p>依赖：${escapeHtml((atom.depends_on || node.depends_on || []).join(", ") || "无")}</p></article>`;
  }).join("") : '<p class="empty-copy">执行图尚未生成。</p>';
}

function renderActions(actions) {
  $("actionList").innerHTML = actions.length ? actions.map((action, index) => `
    <article class="action-card ${escapeHtml(statusClass(action.status))}">
      <span class="sequence">${String(index + 1).padStart(2, "0")}</span>
      <code>${escapeHtml(action.operation || action.action_type || "operation")}</code>
      <p>${escapeHtml(action.action_id || "")} · ${escapeHtml((action.artifact_refs || []).join(", ") || "无产物")}</p>
      <span class="action-status">${escapeHtml(action.status || "pending")}</span>
    </article>`).join("") : '<p class="empty-copy">等待 RWKV Action。</p>';
}

function isEvidenceEvent(item) {
  return /audit|evidence|artifact|action_finished|run_completed/.test(item.type || "");
}

function renderEvidence(contract, events) {
  const verdicts = Object.values(contract.verdicts);
  const satisfied = verdicts.filter((item) => item.status === "satisfied").length;
  const contradicted = verdicts.filter((item) => item.status === "contradicted").length;
  const insufficient = verdicts.filter((item) => item.status === "insufficient").length;
  $("reviewSummary").innerHTML = `
    <article><span>SATISFIED</span><strong>${satisfied}</strong></article>
    <article><span>INSUFFICIENT</span><strong>${insufficient}</strong></article>
    <article><span>CONTRADICTED</span><strong>${contradicted}</strong></article>`;
  $("evidenceTimeline").innerHTML = events.length ? events.slice().reverse().map((item) => `
    <article class="evidence-card"><time>${escapeHtml(time(item.timestamp))}<br>rev ${escapeHtml(item.revision)}</time><strong>${escapeHtml(item.type)}</strong><pre>${escapeHtml(pretty(item.data))}</pre></article>`).join("") : '<p class="empty-copy">尚未产生验收证据。</p>';
}

function renderFiles() {
  $("fileList").innerHTML = app.files.length ? app.files.map((item) => `
    <button class="file-item" data-file-path="${escapeHtml(item.path)}" type="button"><strong>${escapeHtml(item.path)}</strong><span>${bytes(item.size_bytes)} · ${escapeHtml(item.sha256.slice(0, 12))}</span></button>`).join("") : '<p class="empty-copy">工作区尚无文件。</p>';
  document.querySelectorAll(".file-item").forEach((button) => button.addEventListener("click", () => previewFile(button.dataset.filePath, button)));
}

async function previewFile(path, button) {
  document.querySelectorAll(".file-item").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const metadata = app.files.find((item) => item.path === path);
  $("filePreviewName").textContent = path;
  $("filePreviewMeta").textContent = metadata ? `${bytes(metadata.size_bytes)} · ${metadata.media_type}` : "";
  try {
    const encoded = path.split("/").map(encodeURIComponent).join("/");
    const response = await fetch(`/api/runs/${encodeURIComponent(app.selectedRun)}/file/${encoded}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = response.headers.get("content-type") || "";
    $("filePreview").textContent = type.startsWith("text/") || /json|javascript|xml/.test(type)
      ? await response.text()
      : `二进制文件（${type}），请从审计包下载。`;
  } catch (error) {
    $("filePreview").textContent = error.message;
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
  await Promise.all([loadTopology(), loadRuns()]);
});
