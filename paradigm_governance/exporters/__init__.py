"""Export governance reports to various formats."""
from paradigm_governance.schemas import GovernanceReport


def export_csv(report: GovernanceReport) -> str:
    """Export a governance report as CSV."""
    lines = ["module,symbols,cohesion,surface,violations"]
    for m in report.metrics:
        cohesion = f"{m.cohesion_ratio:.2f}" if m.cohesion_ratio is not None else ""
        surface = f"{m.public_surface_ratio:.2f}" if m.public_surface_ratio is not None else ""
        violation_count = sum(1 for v in report.violations if v.module == m.name)
        lines.append(f"{m.name},{m.total_symbols},{cohesion},{surface},{violation_count}")
    return "\n".join(lines)


def export_sarif(report: GovernanceReport) -> dict:
    """Export violations in SARIF format for GitHub code scanning."""
    results = []
    for v in report.violations:
        for e in v.evidence:
            results.append({
                "ruleId": v.rule.value,
                "message": {"text": v.detail},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": e.get("source_file", "")},
                        "region": {"startLine": e.get("line", 1)},
                    }
                }],
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "paradigm-governance"}}, "results": results}],
    }
