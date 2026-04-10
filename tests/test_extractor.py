from paradigm_governance.extractor import extract_file
from paradigm_governance.schemas import Language


def test_extract_imports():
    source = "from core.models import User\nimport os\n"
    result = extract_file("api/routes.py", source, Language.PYTHON)
    assert len(result.imports) == 2
    modules = {imp.source_module for imp in result.imports}
    assert "core.models" in modules
    assert "os" in modules


def test_extract_from_import_names():
    source = "from core.models import User, Project\n"
    result = extract_file("api/routes.py", source, Language.PYTHON)
    assert len(result.imports) == 2
    names = {imp.imported_name for imp in result.imports}
    assert names == {"User", "Project"}


def test_extract_classes():
    source = "class MyModel:\n    pass\n\nclass ChildModel(MyModel):\n    pass\n"
    result = extract_file("core/models.py", source, Language.PYTHON)
    assert len(result.classes) == 2
    assert result.classes[0].name == "MyModel"
    assert result.classes[1].name == "ChildModel"
    assert "MyModel" in result.classes[1].base_classes


def test_extract_symbols():
    source = "class Foo:\n    pass\n\ndef bar():\n    pass\n\ndef _private():\n    pass\n"
    result = extract_file("mod.py", source, Language.PYTHON)
    assert "Foo" in result.symbols
    assert "bar" in result.symbols
    assert "_private" in result.symbols


def test_extract_relative_import():
    source = "from .models import User\n"
    result = extract_file("core/service.py", source, Language.PYTHON)
    assert len(result.imports) == 1
    assert result.imports[0].source_module == ".models"
    assert result.imports[0].imported_name == "User"
