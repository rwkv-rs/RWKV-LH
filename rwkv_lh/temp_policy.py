"""Request-level temperature selection for Long-Horizon model calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemperatureSelection:
    request_type: str
    temperature: float
    reason: str


class TemperaturePolicy:
    _base = {
        "goal_parse": 0.03,
        "goal_binding": 0.03,
        "task_decomposition": 0.18,
        "tool_choice": 0.05,
        "tool_action": 0.05,
        "verification_design": 0.03,
        "evidence_extract": 0.02,
        "context_compress": 0.02,
        "validation_cross_check": 0.03,
        "failure_analysis": 0.10,
        "search_strategy": 0.20,
        "replan": 0.28,
        "alternative_generation": 0.32,
        "final_answer": 0.05,
    }
    _strict_types = {
        "goal_parse",
        "goal_binding",
        "tool_choice",
        "tool_action",
        "verification_design",
        "evidence_extract",
        "context_compress",
        "validation_cross_check",
        "failure_analysis",
        "final_answer",
    }

    def decide(
        self,
        request_type: str,
        *,
        generation: int = 1,
        same_failure_count: int = 0,
        complex_task: bool = False,
        new_evidence: bool = False,
    ) -> TemperatureSelection:
        normalized = str(request_type or "").strip().casefold()
        if normalized not in self._base:
            raise ValueError(f"unknown model request type: {request_type}")
        temperature = self._base[normalized]
        reasons = [f"base_{normalized}"]
        if normalized == "task_decomposition" and complex_task:
            temperature = min(0.25, temperature + 0.07)
            reasons.append("complex_task")
        elif normalized == "replan":
            repeated = max(0, int(same_failure_count))
            if new_evidence:
                effective_repeats = 0
                reasons.append("new_evidence_reset")
            else:
                if repeated:
                    reasons.append(f"same_failure_{repeated}")
                generation_adjustment = max(0, int(generation) - 1)
                effective_repeats = max(repeated, generation_adjustment)
            temperature = min(0.55, temperature + 0.08 * effective_repeats)
        elif normalized in self._strict_types and same_failure_count:
            reasons.append("strict_contract_no_temperature_escalation")
        return TemperatureSelection(
            request_type=normalized,
            temperature=round(temperature, 4),
            reason=";".join(reasons),
        )


__all__ = ["TemperaturePolicy", "TemperatureSelection"]
