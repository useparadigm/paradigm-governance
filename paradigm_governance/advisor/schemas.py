"""Pydantic models for LLM-generated architectural advice."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ViolationAdvice(BaseModel):
    violation_id: int
    risk_assessment: str
    recommended_action: Literal["accept", "restructure", "extract_shared_module"]
    action_detail: str
    suggested_depends_on: Optional[list[str]] = None
    effort_estimate: Literal["trivial", "small", "medium", "large"]


class ModulePlacementAdvice(BaseModel):
    module_name: str
    recommended_layer: Optional[str] = None
    recommended_depends_on: list[str] = []
    architectural_rationale: str


class AdviceReport(BaseModel):
    violation_advice: list[ViolationAdvice] = []
    module_advice: list[ModulePlacementAdvice] = []
    summary: str = ""

    def to_markdown(self) -> str:
        lines = ["## AI Architecture Advice", ""]

        if self.summary:
            lines.append(self.summary)
            lines.append("")

        if self.violation_advice:
            lines.append("### Violation Recommendations")
            lines.append("")
            for va in self.violation_advice:
                effort_icon = {"trivial": "🟢", "small": "🟡", "medium": "🟠", "large": "🔴"}
                icon = effort_icon.get(va.effort_estimate, "⚪")
                action_label = va.recommended_action.replace("_", " ").title()
                lines.append(f"**#{va.violation_id + 1}** — {action_label} {icon} `{va.effort_estimate}`")
                lines.append("")
                lines.append(f"**Risk:** {va.risk_assessment}")
                lines.append("")
                lines.append(f"**Action:** {va.action_detail}")
                if va.suggested_depends_on is not None:
                    deps = ", ".join(f'`{d}`' for d in va.suggested_depends_on)
                    lines.append(f"\n**Suggested `depends_on`:** [{deps}]")
                lines.append("")

        if self.module_advice:
            lines.append("### New Module Recommendations")
            lines.append("")
            for ma in self.module_advice:
                lines.append(f"**`{ma.module_name}`**")
                lines.append("")
                if ma.recommended_layer:
                    lines.append(f"- **Layer:** `{ma.recommended_layer}`")
                if ma.recommended_depends_on:
                    deps = ", ".join(f'`{d}`' for d in ma.recommended_depends_on)
                    lines.append(f"- **depends_on:** [{deps}]")
                lines.append(f"- **Rationale:** {ma.architectural_rationale}")
                lines.append("")

        return "\n".join(lines)
