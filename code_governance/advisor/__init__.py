"""LLM-powered architectural advisor for governance violations and new modules."""
from __future__ import annotations

import sys
from pathlib import Path

from code_governance.advisor.context import build_context
from code_governance.advisor.prompts import SYSTEM_PROMPT, build_user_prompt
from code_governance.advisor.providers import ConfigError, get_provider
from code_governance.advisor.schemas import AdviceReport
from code_governance.config import load_config
from code_governance.engine import discover_dependencies, run_governance
from code_governance.schemas import GovernanceReport


def generate_advice(
    config_path: str | Path,
    governance_report: GovernanceReport | None = None,
    new_modules: list[dict] | None = None,
) -> AdviceReport | None:
    """Generate LLM-powered architectural advice.

    Returns None if there's nothing to advise on (no violations, no new modules).
    Raises ConfigError if no LLM API key is configured.
    """
    config_path = Path(config_path)
    config = load_config(config_path)

    if governance_report is None:
        governance_report = run_governance(config_path)

    # Build context
    discover_report = discover_dependencies(config_path)
    context = build_context(config, config_path, governance_report, discover_report)

    if new_modules is not None:
        context["new_modules"] = new_modules

    # Skip if nothing to advise on
    if not context["violations"] and not context["new_modules"]:
        return None

    # Build prompt
    user_prompt = build_user_prompt(context)

    # Call LLM
    provider = get_provider()

    try:
        report = provider.complete(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        print(f"Warning: LLM call failed: {e}", file=sys.stderr)
        return AdviceReport(
            summary=f"LLM advice unavailable: {e}",
        )

    return report
