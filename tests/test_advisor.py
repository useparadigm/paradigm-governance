"""Tests for the advisor module — context building, prompts, provider selection."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from code_governance.advisor.context import (
    build_context,
    _find_new_modules,
    _get_source_snippet,
)
from code_governance.advisor.prompts import SYSTEM_PROMPT, build_user_prompt
from code_governance.advisor.providers import (
    AnthropicProvider,
    ConfigError,
    OpenAIProvider,
    get_provider,
)
from code_governance.advisor.schemas import (
    AdviceReport,
    ModulePlacementAdvice,
    ViolationAdvice,
)
from code_governance.config import load_config
from code_governance.engine import discover_dependencies, run_governance


# --- Schemas ---


def test_advice_report_to_markdown():
    report = AdviceReport(
        summary="The codebase has a clean architecture overall.",
        violation_advice=[
            ViolationAdvice(
                violation_id=0,
                risk_assessment="This creates tight coupling.",
                recommended_action="restructure",
                action_detail="Move shared types to a common module.",
                effort_estimate="small",
            ),
        ],
        module_advice=[
            ModulePlacementAdvice(
                module_name="exporters",
                recommended_layer="infrastructure",
                recommended_depends_on=["core"],
                architectural_rationale="Exporters are I/O-bound output modules.",
            ),
        ],
    )
    md = report.to_markdown()
    assert "🤖 AI:" in md
    assert "Move shared types" in md
    assert "exporters" in md
    assert "infrastructure" in md


def test_empty_advice_report():
    report = AdviceReport(summary="Nothing to report.")
    md = report.to_markdown()
    assert "Nothing to report." in md
    assert "Violation" not in md


# --- Context ---


def test_build_context(sample_config):
    config = load_config(sample_config)
    report = run_governance(sample_config)
    context = build_context(config, sample_config, report)

    assert "config_toml" in context
    assert "[governance]" in context["config_toml"]
    assert "violations" in context
    assert len(context["violations"]) > 0
    assert "metrics" in context


def test_build_context_source_snippets(sample_config):
    config = load_config(sample_config)
    report = run_governance(sample_config)
    context = build_context(config, sample_config, report)

    # Should have source snippets for violations with evidence
    for v in context["violations"]:
        if v["rule"] == "enforce_depends_on":
            assert len(v["source_snippets"]) > 0
            snippet = v["source_snippets"][0]
            assert "file" in snippet
            assert "line" in snippet
            assert "content" in snippet
            assert ">>>" in snippet["content"]  # marker line
            break


def test_get_source_snippet(sample_config):
    source_root = sample_config.parent
    cache = {}
    snippet = _get_source_snippet(source_root, "api/routes.py", 1, cache)
    assert snippet is not None
    assert snippet["file"] == "api/routes.py"
    assert ">>>" in snippet["content"]
    # File should be cached
    assert "api/routes.py" in cache


def test_get_source_snippet_missing_file(sample_config):
    source_root = sample_config.parent
    snippet = _get_source_snippet(source_root, "nonexistent.py", 1, {})
    assert snippet is None


# --- Prompts ---


def test_system_prompt_has_rules():
    assert "enforce_depends_on" in SYSTEM_PROMPT
    assert "no_cycles" in SYSTEM_PROMPT
    assert "enforce_layers" in SYSTEM_PROMPT


def test_build_user_prompt(sample_config):
    config = load_config(sample_config)
    report = run_governance(sample_config)
    context = build_context(config, sample_config, report)
    prompt = build_user_prompt(context)

    assert "governance.toml" in prompt
    assert "Module Metrics" in prompt
    assert "Violation" in prompt


def test_build_user_prompt_with_new_modules(sample_config):
    config = load_config(sample_config)
    report = run_governance(sample_config)
    context = build_context(config, sample_config, report)
    context["new_modules"] = [{"name": "exporters", "path": "exporters/"}]
    prompt = build_user_prompt(context)

    assert "New Modules Detected" in prompt
    assert "exporters" in prompt


# --- Providers ---


def test_get_provider_anthropic():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("GOVERNANCE_LLM_PROVIDER", None)
            provider = get_provider()
            assert isinstance(provider, AnthropicProvider)


def test_get_provider_openai():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("GOVERNANCE_LLM_PROVIDER", None)
        provider = get_provider()
        assert isinstance(provider, OpenAIProvider)


def test_get_provider_override():
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "ant-key",
        "OPENAI_API_KEY": "oai-key",
        "GOVERNANCE_LLM_PROVIDER": "openai",
    }, clear=False):
        provider = get_provider()
        assert isinstance(provider, OpenAIProvider)


def test_get_provider_no_key():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("GOVERNANCE_LLM_PROVIDER", None)
        with pytest.raises(ConfigError):
            get_provider()


# --- CLI integration (no actual LLM calls) ---


def test_advise_flag_no_api_key(sample_config):
    """--advise without API key should print error, not crash."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "code_governance", "--config",
         str(sample_config), "--advise"],
        capture_output=True,
        text=True,
        env={**os.environ, "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""},
    )
    # Should still output the governance report (exits 1 due to violations)
    assert result.returncode == 1
    assert "Governance Report" in result.stdout or "Violations" in result.stdout
