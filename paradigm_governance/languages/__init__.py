from __future__ import annotations

from paradigm_governance.languages.csharp import CSharpPatterns
from paradigm_governance.languages.python import PythonPatterns
from paradigm_governance.languages.typescript import TypeScriptPatterns
from paradigm_governance.schemas import Language

LANGUAGE_PATTERNS = {
    Language.PYTHON: PythonPatterns,
    Language.TYPESCRIPT: TypeScriptPatterns,
    Language.CSHARP: CSharpPatterns,
}


def get_patterns(language: Language):
    cls = LANGUAGE_PATTERNS.get(language)
    if cls is None:
        raise ValueError(f"Unsupported language: {language}")
    return cls()
