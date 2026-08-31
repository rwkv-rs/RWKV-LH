"""Generate the frozen Stage-0 RWKV State Router 2K corpus.

The dataset is grouped by semantic family before splitting.  Summary variants
never define execution truth: labels are derived from the explicit controller
evidence and Network Gate fields plus the scenario's required capability.
Existing ECRA and E2E requests are holdouts and are used only for contamination
checks, never as generation seeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rwkv_lh.state_router.protocol import (
    ContextMode,
    EvidenceState,
    ExecutionPhase,
    NetworkRecommendation,
    PolicyState,
    RouteFamily,
    RouterInput,
    mechanical_execution_phase,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1"
VERSION = "rwkv-lh.state-router-2k.v1"
SCHEMA = "rwkv-lh.state-router-sample.v1"
GENERATOR_VERSION = "rwkv-lh.state-router-generator.v1"
SIMILARITY_VERSION = "utf8-byte-ngram-cosine.v1"
SIMILARITY_N = 5
CONTAMINATION_THRESHOLD = 0.75

ROUTE_COUNTS = {
    RouteFamily.LOCAL: 45,
    RouteFamily.DETERMINISTIC: 30,
    RouteFamily.WEB: 50,
    RouteFamily.CONNECTOR: 45,
    RouteFamily.MIXED: 35,
    RouteFamily.FINAL: 25,
    RouteFamily.ABSTAIN: 20,
}
SPLIT_ROUTE_COUNTS = {
    "train": {
        RouteFamily.LOCAL: 31,
        RouteFamily.DETERMINISTIC: 21,
        RouteFamily.WEB: 35,
        RouteFamily.CONNECTOR: 31,
        RouteFamily.MIXED: 25,
        RouteFamily.FINAL: 18,
        RouteFamily.ABSTAIN: 14,
    },
    "dev": {
        RouteFamily.LOCAL: 7,
        RouteFamily.DETERMINISTIC: 4,
        RouteFamily.WEB: 7,
        RouteFamily.CONNECTOR: 7,
        RouteFamily.MIXED: 5,
        RouteFamily.FINAL: 4,
        RouteFamily.ABSTAIN: 3,
    },
    "test": {
        RouteFamily.LOCAL: 7,
        RouteFamily.DETERMINISTIC: 5,
        RouteFamily.WEB: 8,
        RouteFamily.CONNECTOR: 7,
        RouteFamily.MIXED: 5,
        RouteFamily.FINAL: 3,
        RouteFamily.ABSTAIN: 3,
    },
}
EXPECTED_SPLIT_SAMPLES = {"train": 1400, "dev": 300, "test": 300}

SOURCE_FILES = (
    "data/experiments/RWKV_ACTION_STATE_TUNING_ROUND1_2K_V1_20260826/failure_registry.jsonl",
    "data/datasets/rwkv_lh_state_tuning_stage6_final_balance_v1/residual_registry.json",
    "data/experiments/RWKV_ECRA_ROUTE_V2_CANARY_20260825/R9_ANALYSIS.md",
)
HOLDOUT_FILES = (
    "data/datasets/rwkv_lh_ecra_route_v1/cases.json",
    "benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json",
    "benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json",
    "benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json",
)


@dataclass(frozen=True)
class FamilySpec:
    ordinal: int
    route: RouteFamily
    request: str
    alternate_request: str
    true_summary: str
    required_facts: tuple[str, ...]
    why_route: str
    why_not_other_routes: str
    boundary_id: str
    language: str

    @property
    def family_id(self) -> str:
        return f"RTR2K-SF-{self.ordinal + 1:04d}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def make_local(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        path = f"configs/router-{slot:03d}.toml"
        request = f"读取本地 `{path}`，报告 `[runtime]` 下的 backend 和 timeout。"
        alternate = f"请直接检查仓库文件 `{path}` 的 runtime backend 与 timeout 两项。"
        facts = (f"{path} content", "runtime.backend", "runtime.timeout")
    elif pattern == 1:
        symbol = f"RouteBoundary{slot:03d}"
        request = f"Find every definition and reference of `{symbol}` in this workspace."
        alternate = f"Search the checked-out source tree for all uses of `{symbol}`."
        facts = (f"workspace matches for {symbol}",)
    elif pattern == 2:
        database = f"data/local-audit-{slot:03d}.sqlite"
        request = f"查询本地 `{database}` 的 jobs 表，统计 status='failed' 的行数。"
        alternate = f"只使用仓库中的 SQLite 文件 `{database}` 计算失败 job 数。"
        facts = (f"{database}:jobs", "failed row count")
    elif pattern == 3:
        left = f"snapshots/left-{slot:03d}.json"
        right = f"snapshots/right-{slot:03d}.json"
        request = f"Compare local files `{left}` and `{right}` and list changed top-level keys."
        alternate = f"Inspect `{left}` versus `{right}` in the workspace; return the top-level key delta."
        facts = (left, right, "top-level key delta")
    else:
        test_path = f"tests/router_case_{slot:03d}.py"
        request = f"运行本地 `{test_path}`，如果失败就给出首个 traceback 的文件和行号。"
        alternate = f"Execute the repository test `{test_path}` and locate the first failing source line."
        facts = (test_path, "local test result", "first traceback frame")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.LOCAL,
        request=request,
        alternate_request=alternate,
        true_summary=f"The active request concerns only workspace-local evidence for case {slot:03d}.",
        required_facts=facts,
        why_route="The requested evidence is stored in the local workspace or local process.",
        why_not_other_routes="No current public fact or authorized private account resource is required.",
        boundary_id=("FST-R1-005" if pattern == 0 else "FST-R1-008" if pattern in {1, 3} else "FST-R1-009"),
        language=language,
    )


def make_deterministic(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        a, b = 37 + slot, 11 + (slot % 9)
        request = f"精确计算 `({a} * {b}) + {slot ** 2}`。"
        alternate = f"Use deterministic arithmetic to evaluate ({a}×{b})+{slot ** 2}."
        facts = ("arithmetic expression",)
    elif pattern == 1:
        amount = 1250 + slot * 17
        request = f"Convert exactly {amount} KiB to bytes using 1 KiB = 1024 bytes."
        alternate = f"按二进制单位把 {amount} KiB 精确换算成 byte。"
        facts = ("unit definition", "converted byte count")
    elif pattern == 2:
        day = 1 + slot % 20
        year = 2026 + index // 20
        request = f"计算 {year}-03-{day:02d} 到 {year}-11-{day:02d} 相差多少天（用例 {slot:03d}）。"
        alternate = f"Return the exact day difference between {year}-03-{day:02d} and {year}-11-{day:02d} for case {slot:03d}."
        facts = ("two fixed dates", "day difference")
    elif pattern == 3:
        hour = 8 + slot % 8
        request = f"Convert the fixed time 2026-01-15 {hour:02d}:30 UTC to Asia/Shanghai."
        alternate = f"把固定 UTC 时间 2026-01-15 {hour:02d}:30 转为上海时区。"
        facts = ("fixed UTC timestamp", "timezone conversion")
    else:
        value = {"case": slot, "enabled": bool(slot % 2), "weight": slot * 3}
        request = f"Canonicalize this supplied JSON with sorted keys and no extra spaces: {json.dumps(value)}"
        alternate = f"将给定 JSON 按 key 排序并压缩为规范形式：{json.dumps(value)}"
        facts = ("provided JSON value", "canonical serialization")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.DETERMINISTIC,
        request=request,
        alternate_request=alternate,
        true_summary=f"Case {slot:03d} is fully specified and needs a deterministic transform.",
        required_facts=facts,
        why_route="All inputs are fixed and the answer is produced by deterministic computation.",
        why_not_other_routes="No workspace discovery, public web fact or private connector data is needed.",
        boundary_id="SYSTEM-BOUNDARY-DETERMINISTIC-V1",
        language=language,
    )


def make_web(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        project = f"public-router-lib-{slot:03d}"
        request = f"查找公开项目 `{project}` 截至今天的最新稳定版本和发布日期。"
        alternate = f"Look up the current stable public release and release date for `{project}`."
        facts = (f"current release for {project}", "publication date")
    elif pattern == 1:
        city = ("Reykjavik", "Osaka", "Valencia", "Nairobi", "Halifax")[index % 5]
        request = f"What is the official public weather warning status for {city} today? Query reference {slot:03d}."
        alternate = f"查询 {city} 今天公开发布的天气预警状态；查询引用 {slot:03d}。"
        facts = (f"current public weather alert for {city}",)
    elif pattern == 2:
        standard = f"RFC-{9300 + slot}"
        request = f"查找 `{standard}` 的公开最新状态，以及最后更新时间。"
        alternate = f"Check the current public status and last-update date of `{standard}`."
        facts = (f"current status of {standard}", "last updated date")
    elif pattern == 3:
        event = f"Open Systems Forum {2026 + slot % 3}-{slot:03d}"
        request = f"Find the currently published schedule and venue for the public event `{event}`."
        alternate = f"查询公开活动 `{event}` 目前公布的日程与地点。"
        facts = (f"current schedule for {event}", "venue")
    else:
        package = f"router-public-pkg-{slot:03d}"
        request = f"查阅公开包注册表，给出 `{package}` 当前版本及其许可证元数据。"
        alternate = f"Use public sources to find the current version and license metadata of `{package}`."
        facts = (f"current registry record for {package}", "license metadata")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.WEB,
        request=request,
        alternate_request=alternate,
        true_summary=f"The unresolved fact in case {slot:03d} is current and publicly accessible.",
        required_facts=facts,
        why_route="The answer depends on a current public fact not present in local evidence.",
        why_not_other_routes="The source is public and does not require an authenticated private account.",
        boundary_id="STAGE6-RESIDUAL-PUBLIC-WEB",
        language=language,
    )


def make_connector(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        issue = 7000 + slot
        request = f"读取我已授权的私有 GitHub 仓库 `acme/router-lab` 中 issue #{issue} 的当前 assignee。"
        alternate = f"Use my connected GitHub account to get the assignee of private issue acme/router-lab#{issue}."
        facts = (f"private GitHub issue {issue}", "assignee")
    elif pattern == 1:
        path = f"/Router Audits/quarter-{slot:03d}.pdf"
        request = f"Open my connected Dropbox file `{path}` and report its approval status."
        alternate = f"从已授权 Dropbox 的 `{path}` 读取审批状态。"
        facts = (f"private Dropbox file {path}", "approval status")
    elif pattern == 2:
        record = f"recRouter{slot:04d}"
        request = f"查询我已连接 Airtable 的 private Routing Runs 表中 `{record}` 的 owner 字段。"
        alternate = f"Read the owner for private Airtable Routing Runs record `{record}` from my account."
        facts = (f"private Airtable record {record}", "owner")
    elif pattern == 3:
        meeting = f"Router calibration {slot:03d}"
        request = f"Find the action items in my authorized Fathom meeting named `{meeting}`."
        alternate = f"从我的 Fathom 连接器读取会议 `{meeting}` 的 action items。"
        facts = (f"private Fathom meeting {meeting}", "action items")
    else:
        task = f"RTR-CONN-{slot:04d}"
        request = f"读取我 Todoist 账户中私有任务 `{task}` 的 due date 和 labels。"
        alternate = f"Use the connected Todoist account for private task `{task}` and return its due date and labels."
        facts = (f"private Todoist task {task}", "due date", "labels")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.CONNECTOR,
        request=request,
        alternate_request=alternate,
        true_summary=f"Case {slot:03d} targets an explicitly authorized private account resource.",
        required_facts=facts,
        why_route="The requested resource is private account data behind an authenticated connector.",
        why_not_other_routes="Ordinary public web search must not substitute for private authorized data.",
        boundary_id="STAGE6-RESIDUAL-WEB-CONNECTOR",
        language=language,
    )


def make_mixed(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        path = f"packages/router-target-{slot:03d}.txt"
        request = f"先读取本地 `{path}` 中的包名，再查询其公开注册表当前稳定版本。"
        alternate = f"Read the package name from local `{path}`, then look up that package's current public release."
        facts = (f"local {path}", "current public package release")
    elif pattern == 1:
        path = f"accounts/customer-{slot:03d}.json"
        request = f"Read the customer ID from local `{path}`, then retrieve that customer's private Airtable renewal date."
        alternate = f"从本地 `{path}` 绑定 customer ID，再通过授权 Airtable 查询续约日期。"
        facts = (f"local customer id in {path}", "private Airtable renewal date")
    elif pattern == 2:
        commodity = f"PublicIndex-{slot:03d}"
        request = f"查询 `{commodity}` 当前公开值，并计算相对给定基线 {1000 + slot} 的百分比变化。"
        alternate = f"Get the current public `{commodity}` value, then deterministically compute change from baseline {1000 + slot}."
        facts = (f"current public {commodity} value", "percentage calculation")
    elif pattern == 3:
        path = f"meetings/target-{slot:03d}.txt"
        request = f"Read the meeting title from local `{path}`, then fetch its private Fathom action items."
        alternate = f"先从本地 `{path}` 取会议名，再通过已授权 Fathom 读取 action items。"
        facts = (f"local meeting title in {path}", "private Fathom action items")
    else:
        path = f"pyproject-router-{slot:03d}.toml"
        request = f"读取本地 `{path}` 的依赖约束，再核对该依赖当前公开文档是否仍兼容。"
        alternate = f"Inspect the dependency constraint in local `{path}` and compare it with current public compatibility docs."
        facts = (f"local dependency in {path}", "current public compatibility documentation")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.MIXED,
        request=request,
        alternate_request=alternate,
        true_summary=f"Case {slot:03d} has two bound stages across distinct capability families.",
        required_facts=facts,
        why_route="The requested result requires a bound sequence across more than one tool family.",
        why_not_other_routes="A single local, deterministic, web or connector route cannot supply all required facts.",
        boundary_id="FST-R1-006",
        language=language,
    )


def make_final(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        request = f"用两句话解释：RWKV 的 recurrent state 为什么能让解码保持常量级上下文存储。编号 {slot:03d}。"
        alternate = f"In two sentences, explain how recurrent state gives RWKV constant-memory decoding (case {slot:03d})."
        facts = ("stable conceptual explanation",)
    elif pattern == 1:
        text = f"Router sample {slot:03d} is complete and verified."
        request = f"Translate this supplied sentence into Chinese: `{text}`"
        alternate = f"把给定句子译成中文，不补充外部事实：`{text}`"
        facts = ("supplied sentence",)
    elif pattern == 2:
        text = f"state router case {slot:03d}: evidence wins over summaries"
        request = f"Rewrite the supplied text in title case: `{text}`"
        alternate = f"将给定文本 `{text}` 改成英文标题大小写。"
        facts = ("supplied text",)
    elif pattern == 3:
        request = f"Explain the difference between a recommendation and an authorization, using State Router case {slot:03d} as a generic example."
        alternate = f"用 State Router 示例 {slot:03d} 说明“建议”和“授权”的区别。"
        facts = ("stable protocol distinction",)
    else:
        text = f"Evidence is committed; redundant calls add risk ({slot:03d})."
        request = f"Summarize this supplied sentence in at most eight words: `{text}`"
        alternate = f"将给定句子压缩到八个英文单词以内：`{text}`"
        facts = ("supplied sentence",)
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.FINAL,
        request=request,
        alternate_request=alternate,
        true_summary=f"All information needed for direct response case {slot:03d} is already in the request or stable model knowledge.",
        required_facts=facts,
        why_route="The request is answerable from supplied content or stable conceptual knowledge.",
        why_not_other_routes="Calling a tool would not add required evidence and would be redundant.",
        boundary_id="FST-R1-012",
        language=language,
    )


def make_abstain(index: int, ordinal: int) -> FamilySpec:
    slot = index + 1
    language = "zh" if index % 2 == 0 else "en"
    pattern = index % 5
    if pattern == 0:
        request = f"像上次一样处理那个报告。歧义样本 {slot:03d}。"
        alternate = f"Handle that report the same way as before (ambiguous sample {slot:03d})."
        facts = ("missing report identity", "missing prior operation")
    elif pattern == 1:
        request = f"Open the dashboard and fix it, case {slot:03d}."
        alternate = f"打开那个 dashboard 并修好它，样本 {slot:03d}。"
        facts = ("missing dashboard location", "missing defect description")
    elif pattern == 2:
        request = f"Use the appropriate source for item `{slot:03d}` and continue."
        alternate = f"为条目 `{slot:03d}` 选择合适来源后继续，但未提供条目类型。"
        facts = ("missing item type", "missing source scope")
    elif pattern == 3:
        request = f"检查它是不是最新的，然后照常更新，编号 {slot:03d}。"
        alternate = f"Check whether it is current and update it normally, item {slot:03d}; no referent is supplied."
        facts = ("missing referent", "missing update authority")
    else:
        request = f"Route ambiguous object `{slot:03d}` without revealing whether it is local, public, or private."
        alternate = f"路由歧义对象 `{slot:03d}`；没有说明它在本地、公开网络还是私有账户。"
        facts = ("missing capability location", "missing authorization context")
    return FamilySpec(
        ordinal=ordinal,
        route=RouteFamily.ABSTAIN,
        request=request,
        alternate_request=alternate,
        true_summary=f"Case {slot:03d} remains underspecified; its object and capability location are unknown.",
        required_facts=facts,
        why_route="The request is underspecified or outside the route distribution, so choosing a family would be unsafe.",
        why_not_other_routes="Local, web, connector, mixed and final each require facts that the request withholds.",
        boundary_id="SYSTEM-BOUNDARY-OOD-ABSTAIN-V1",
        language=language,
    )


FACTORIES = {
    RouteFamily.LOCAL: make_local,
    RouteFamily.DETERMINISTIC: make_deterministic,
    RouteFamily.WEB: make_web,
    RouteFamily.CONNECTOR: make_connector,
    RouteFamily.MIXED: make_mixed,
    RouteFamily.FINAL: make_final,
    RouteFamily.ABSTAIN: make_abstain,
}


def build_families() -> list[FamilySpec]:
    families: list[FamilySpec] = []
    for route, count in ROUTE_COUNTS.items():
        factory = FACTORIES[route]
        for index in range(count):
            families.append(factory(index, len(families)))
    if len(families) != 250:
        raise RuntimeError(f"family inventory mismatch: {len(families)}")
    return families


def assign_splits(families: Sequence[FamilySpec]) -> dict[str, str]:
    grouped: dict[RouteFamily, list[FamilySpec]] = defaultdict(list)
    for family in families:
        grouped[family.route].append(family)
    assignment: dict[str, str] = {}
    for route, route_families in grouped.items():
        cursor = 0
        for split in ("train", "dev", "test"):
            count = SPLIT_ROUTE_COUNTS[split][route]
            for family in route_families[cursor : cursor + count]:
                assignment[family.family_id] = split
            cursor += count
        if cursor != len(route_families):
            raise RuntimeError(f"split inventory mismatch for {route.value}")
    return assignment


def current_labels(
    family: FamilySpec,
    router_input: RouterInput,
    *,
    evidence_committed_closes_route: bool = True,
) -> tuple[ExecutionPhase, RouteFamily, NetworkRecommendation]:
    underlying_network = (
        NetworkRecommendation.REQUIRED
        if family.route in {RouteFamily.WEB, RouteFamily.CONNECTOR, RouteFamily.MIXED}
        else NetworkRecommendation.NOT_REQUIRED
    )
    if family.route is RouteFamily.ABSTAIN:
        route = RouteFamily.ABSTAIN
        network = NetworkRecommendation.NOT_REQUIRED
    elif (
        evidence_committed_closes_route
        and router_input.evidence_state is EvidenceState.COMMITTED
    ):
        route = RouteFamily.FINAL
        network = NetworkRecommendation.NOT_REQUIRED
    else:
        route = family.route
        network = underlying_network
    phase = mechanical_execution_phase(
        router_input,
        candidate_route=route,
        network_recommendation=network,
    )
    return phase, route, network


def variant_specs(
    family: FamilySpec,
    *,
    split: str,
    add_true_summary: bool,
    remove_misleading_partial: bool,
    policy_denied: bool,
) -> list[tuple[str, RouterInput]]:
    specs: list[tuple[str, RouterInput]] = []

    def add(
        kind: str,
        *,
        mode: ContextMode,
        summary: str | None,
        evidence: EvidenceState,
        policy: PolicyState = PolicyState.NETWORK_ALLOWED,
        request: str | None = None,
    ) -> None:
        sample_number = len(specs) + 1
        specs.append(
            (
                kind,
                RouterInput(
                    mode=mode,
                    summary=summary,
                    evidence_state=evidence,
                    policy_state=policy,
                    request=request or family.request,
                    trace_id=f"{family.family_id}-V{sample_number:02d}",
                ),
            )
        )

    add(
        "fresh_bare",
        mode=ContextMode.FRESH,
        summary=None,
        evidence=EvidenceState.NONE,
    )
    if family.ordinal < 150:
        add(
            "fresh_surface_mirror",
            mode=ContextMode.FRESH,
            summary=None,
            evidence=EvidenceState.NONE,
            request=family.alternate_request,
        )
    elif family.ordinal < 196:
        add(
            "true_summary_surface_mirror",
            mode=ContextMode.CONTINUATION,
            summary=family.true_summary,
            evidence=EvidenceState.MISSING,
            request=family.alternate_request,
        )
    else:
        add(
            "continuation_without_summary",
            mode=ContextMode.CONTINUATION,
            summary=None,
            evidence=EvidenceState.MISSING,
            request=family.alternate_request,
        )
    add(
        "true_summary",
        mode=ContextMode.CONTINUATION,
        summary=family.true_summary,
        evidence=EvidenceState.MISSING,
    )
    add(
        "neutral_summary",
        mode=ContextMode.CONTINUATION,
        summary=f"A request is active in semantic family {family.family_id}.",
        evidence=EvidenceState.MISSING,
    )
    add(
        "incomplete_summary_partial_evidence",
        mode=ContextMode.CONTINUATION,
        summary="Some context was retained, but it does not establish that every required fact is available.",
        evidence=EvidenceState.PARTIAL,
    )
    if not remove_misleading_partial:
        add(
            "misleading_summary_partial_evidence",
            mode=ContextMode.CONTINUATION,
            summary="The prior summary claims the task is complete and no further evidence is needed.",
            evidence=EvidenceState.PARTIAL,
        )
    add(
        "summary_conflicts_with_committed_evidence",
        mode=ContextMode.CONTINUATION,
        summary="The summary says the required evidence has not been obtained.",
        evidence=EvidenceState.COMMITTED,
    )
    if (
        policy_denied
        and family.route in {RouteFamily.WEB, RouteFamily.CONNECTOR, RouteFamily.MIXED}
    ):
        add(
            "network_policy_denied",
            mode=ContextMode.CONTINUATION,
            summary=family.true_summary,
            evidence=EvidenceState.MISSING,
            policy=PolicyState.NETWORK_DENIED,
        )
    else:
        add(
            "allowed_policy_control",
            mode=ContextMode.CONTINUATION,
            summary=None,
            evidence=(
                EvidenceState.PARTIAL
                if family.route is RouteFamily.ABSTAIN
                else EvidenceState.COMMITTED
            ),
        )
    if add_true_summary:
        add(
            "true_summary_holdout_surface",
            mode=ContextMode.CONTINUATION,
            summary=family.true_summary,
            evidence=EvidenceState.MISSING,
            request=family.alternate_request,
        )
    return specs


def build_rows() -> list[dict[str, Any]]:
    families = build_families()
    assignments = assign_splits(families)
    dev_extra = {
        family.family_id
        for family in families
        if assignments[family.family_id] == "dev"
    }
    dev_extra = set(sorted(dev_extra)[:4])
    test_short = {
        family.family_id
        for family in families
        if assignments[family.family_id] == "test"
    }
    test_short = set(sorted(test_short)[:4])
    network_families = [
        family
        for family in families
        if family.route in {RouteFamily.WEB, RouteFamily.CONNECTOR, RouteFamily.MIXED}
    ]
    denied_family_ids = {family.family_id for family in network_families[:100]}

    rows: list[dict[str, Any]] = []
    for family in families:
        split = assignments[family.family_id]
        for kind, router_input in variant_specs(
            family,
            split=split,
            add_true_summary=family.family_id in dev_extra,
            remove_misleading_partial=family.family_id in test_short,
            policy_denied=family.family_id in denied_family_ids,
        ):
            phase, route, network = current_labels(family, router_input)
            sample_id = f"RTR2K-{len(rows) + 1:04d}"
            design_axes = [
                "fresh_input" if router_input.mode is ContextMode.FRESH else "continuation",
                kind,
                f"route_boundary:{family.route.value}",
                f"evidence:{router_input.evidence_state.value}",
                f"policy:{router_input.policy_state.value}",
            ]
            rows.append(
                {
                    "schema_version": SCHEMA,
                    "dataset_version": VERSION,
                    "sample_id": sample_id,
                    "semantic_family_id": family.family_id,
                    "split": split,
                    "source": {
                        "kind": "historical_failure_or_explicit_system_boundary",
                        "boundary_id": family.boundary_id,
                    },
                    "generator_version": GENERATOR_VERSION,
                    "language": family.language,
                    "variant_kind": kind,
                    "design_axes": design_axes,
                    "input": router_input.to_dict(),
                    "labels": {
                        "context_mode": router_input.mode.value,
                        "execution_phase": phase.value,
                        "route_family": route.value,
                        "network_recommendation": network.value,
                    },
                    "rationale": {
                        "required_facts": list(family.required_facts),
                        "why_route": family.why_route,
                        "why_not_other_routes": family.why_not_other_routes,
                        "authority": "controller_and_gate_facts_override_summary",
                    },
                }
            )
    return rows


def byte_ngrams(value: str, n: int = SIMILARITY_N) -> Counter[bytes]:
    encoded = value.casefold().encode("utf-8")
    if len(encoded) < n:
        return Counter({encoded: 1}) if encoded else Counter()
    return Counter(encoded[index : index + n] for index in range(len(encoded) - n + 1))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    shared = left.keys() & right.keys()
    numerator = sum(left[key] * right[key] for key in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm)


def holdout_requests() -> list[tuple[str, str]]:
    requests: list[tuple[str, str]] = []
    for relative in HOLDOUT_FILES:
        path = ROOT / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        records = value.get("cases") if isinstance(value, Mapping) else value
        if isinstance(value, Mapping) and records is None:
            records = value.get("tasks")
        if not isinstance(records, list):
            raise RuntimeError(f"unsupported holdout structure: {relative}")
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                continue
            request = (
                record.get("request")
                or record.get("instruction")
                or record.get("user_request")
                or record.get("prompt")
                or record.get("goal")
            )
            if request:
                requests.append((f"{relative}:{index}", str(request)))
    return requests


def audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(rows) != 2000:
        raise RuntimeError(f"expected 2000 rows, got {len(rows)}")
    sample_ids = [str(row["sample_id"]) for row in rows]
    if len(set(sample_ids)) != len(sample_ids):
        raise RuntimeError("duplicate sample_id")
    by_split = Counter(str(row["split"]) for row in rows)
    if dict(by_split) != EXPECTED_SPLIT_SAMPLES:
        raise RuntimeError(f"split counts mismatch: {dict(by_split)}")

    family_splits: dict[str, set[str]] = defaultdict(set)
    family_variants: Counter[str] = Counter()
    rendered_inputs: Counter[str] = Counter()
    for row in rows:
        family = str(row["semantic_family_id"])
        family_splits[family].add(str(row["split"]))
        family_variants[family] += 1
        router_input = RouterInput.from_dict(row["input"])
        rendered_inputs[router_input.render()] += 1
        labels = row["labels"]
        ContextMode(str(labels["context_mode"]))
        ExecutionPhase(str(labels["execution_phase"]))
        RouteFamily(str(labels["route_family"]))
        NetworkRecommendation(str(labels["network_recommendation"]))
    leaking = {family: splits for family, splits in family_splits.items() if len(splits) != 1}
    if leaking:
        raise RuntimeError(f"semantic family split leakage: {leaking}")
    if len(family_splits) != 250 or min(family_variants.values()) < 7:
        raise RuntimeError("semantic family coverage is incomplete")
    duplicate_inputs = sum(count - 1 for count in rendered_inputs.values() if count > 1)
    if duplicate_inputs:
        raise RuntimeError(f"exact rendered input duplicates: {duplicate_inputs}")

    variant_counts = Counter(str(row["variant_kind"]) for row in rows)
    fresh_count = sum(
        1 for row in rows if row["input"]["mode"] == ContextMode.FRESH.value
    )
    true_summary_count = sum(
        1 for row in rows if str(row["variant_kind"]).startswith("true_summary")
    )
    policy_denied_count = sum(
        1
        for row in rows
        if row["input"]["policy_state"] == PolicyState.NETWORK_DENIED.value
    )
    if fresh_count != 400 or true_summary_count != 300 or policy_denied_count != 100:
        raise RuntimeError(
            "design quota mismatch: "
            f"fresh={fresh_count} true_summary={true_summary_count} "
            f"policy_denied={policy_denied_count}"
        )

    generated_requests: dict[str, str] = {}
    for row in rows:
        generated_requests.setdefault(
            str(row["semantic_family_id"]), str(row["input"]["request"])
        )
    holdouts = holdout_requests()
    holdout_vectors = [(identifier, text, byte_ngrams(text)) for identifier, text in holdouts]
    maximum = 0.0
    nearest: dict[str, Any] = {}
    for family, request in generated_requests.items():
        vector = byte_ngrams(request)
        for identifier, holdout, holdout_vector in holdout_vectors:
            score = cosine(vector, holdout_vector)
            if score > maximum:
                maximum = score
                nearest = {
                    "semantic_family_id": family,
                    "holdout_id": identifier,
                    "score": score,
                    "generated_request": request,
                    "holdout_request": holdout,
                }
    if maximum >= CONTAMINATION_THRESHOLD:
        raise RuntimeError(f"holdout contamination threshold exceeded: {nearest}")

    return {
        "sample_count": len(rows),
        "semantic_family_count": len(family_splits),
        "split_sample_counts": dict(sorted(by_split.items())),
        "split_family_counts": dict(
            sorted(Counter(next(iter(splits)) for splits in family_splits.values()).items())
        ),
        "variant_counts": dict(sorted(variant_counts.items())),
        "fresh_input_count": fresh_count,
        "true_summary_count": true_summary_count,
        "network_policy_denied_count": policy_denied_count,
        "label_counts": {
            name: dict(
                sorted(Counter(str(row["labels"][name]) for row in rows).items())
            )
            for name in (
                "context_mode",
                "execution_phase",
                "route_family",
                "network_recommendation",
            )
        },
        "family_split_overlap_count": 0,
        "exact_rendered_input_duplicate_count": 0,
        "contamination": {
            "similarity_version": SIMILARITY_VERSION,
            "n": SIMILARITY_N,
            "threshold_exclusive": CONTAMINATION_THRESHOLD,
            "holdout_request_count": len(holdouts),
            "maximum_holdout_similarity": maximum,
            "nearest_holdout": nearest,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    rows = build_rows()
    validation = audit(rows)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "samples.jsonl", rows)
    for split in ("train", "dev", "test"):
        write_jsonl(
            output / f"{split}.jsonl",
            (row for row in rows if row["split"] == split),
        )
    readme = """# RWKV-LH State Router 2K v1

- 来源：历史 RWKV-LH 路由/停止缺陷签名与设计稿中冻结的显式系统边界；不使用 ECRA/E2E 请求作为生成种子。
- 版本：`rwkv-lh.state-router-2k.v1`。
- 用途：阶段 0 离线 State Router 多头分类；不得作为主模型任务答案 SFT。
- 生成：`uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_state_router_2k_v1.py`。
- 切分：semantic-family 分组的 train/dev/test = 1400/300/300；同族镜像不会跨 split。
- 协议：最终层有效 token mean-pooled hidden；机械 evidence/policy 真值高于 Summary。
- 污染检查：`utf8-byte-ngram-cosine.v1`，byte 5-gram，ECRA120 与 E2E90 固定 holdout，阈值 `<0.75`。
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    file_names = ("README.md", "samples.jsonl", "train.jsonl", "dev.jsonl", "test.jsonl")
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "source": "historical RWKV-LH residual signatures and explicit State Router system boundaries",
        "purpose": "Stage-0 offline multi-head State Router classification",
        "generation": "uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_state_router_2k_v1.py",
        "generator_version": GENERATOR_VERSION,
        "feature_protocol": "rwkv-lh.final-hidden-mean.v1",
        "split_protocol": "semantic-family-grouped-70-15-15.v1",
        "summary_authority": False,
        "controller_and_gate_authority": True,
        "validation": validation,
        "sources": {
            relative: {"sha256": sha256(ROOT / relative)} for relative in SOURCE_FILES
        },
        "holdouts": {
            relative: {"sha256": sha256(ROOT / relative)} for relative in HOLDOUT_FILES
        },
        "generator": {
            "path": "scripts/generate_state_router_2k_v1.py",
            "sha256": sha256(Path(__file__).resolve()),
        },
        "files": {
            name: {
                "sha256": sha256(output / name),
                "bytes": (output / name).stat().st_size,
            }
            for name in file_names
        },
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
