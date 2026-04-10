"""Debug helper — render extraction results as HTML."""
from paradigm_governance.schemas import FileExtractionResult


def render_debug_html(result: FileExtractionResult) -> str:
    from paradigm_governance.viewer.index import TEMPLATE
    return TEMPLATE.replace("__REPORT_DATA__", f"<pre>{result}</pre>")
