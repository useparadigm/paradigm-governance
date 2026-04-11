"""Pydantic models for LLM-generated architectural advice."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ViolationAdvice(BaseModel):
    violation_id: int
    risk_assessment: str
    recommended_action: Literal["accept", "restructure", "extract_shared_module"]
    action_detail: str
    suggested_cannot_depend_on: Optional[list[str]] = None
    effort_estimate: Literal["trivial", "small", "medium", "large"]


class ModulePlacementAdvice(BaseModel):
    module_name: str
    recommended_layer: Optional[str] = None
    recommended_cannot_depend_on: list[str] = []
    architectural_rationale: str


class AdviceReport(BaseModel):
    violation_advice: list[ViolationAdvice] = []
    module_advice: list[ModulePlacementAdvice] = []
    summary: str = ""

    def to_markdown(self) -> str:
        lines = []
        effort_icon = {"trivial": "🟢", "small": "🟡", "medium": "🟠", "large": "🔴"}
        action_icon = {"accept": "✅", "restructure": "🔧", "extract_shared_module": "📦"}

        if self.summary:
            lines.append(f"**🤖 AI:** {self.summary}")
            lines.append("")

        for va in self.violation_advice:
            e = effort_icon.get(va.effort_estimate, "⚪")
            a = action_icon.get(va.recommended_action, "💡")
            deps = ""
            if va.suggested_cannot_depend_on is not None:
                deps = f" → `cannot_depend_on: {va.suggested_cannot_depend_on}`"
            lines.append(f"{a} **#{va.violation_id + 1}** {va.action_detail}{deps} {e}")

        for ma in self.module_advice:
            deps = ", ".join(f"`{d}`" for d in ma.recommended_cannot_depend_on) if ma.recommended_cannot_depend_on else "none"
            layer = f"layer=`{ma.recommended_layer}` " if ma.recommended_layer else ""
            lines.append(f"📦 **`{ma.module_name}`**: {layer}cannot_depend_on=[{deps}]. {ma.architectural_rationale}")

        return "\n".join(lines)
