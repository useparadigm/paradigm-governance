import pytest
from pathlib import Path

from code_governance.config import load_config


def test_load_valid_config(sample_config):
    config = load_config(sample_config)
    assert config.language.value == "python"
    assert config.root == "."
    assert len(config.modules) == 4
    module_names = {m.name for m in config.modules}
    assert module_names == {"core", "db", "api", "utils"}


def test_load_config_modules_have_correct_deps(sample_config):
    config = load_config(sample_config)
    by_name = {m.name: m for m in config.modules}
    assert by_name["core"].depends_on == []
    assert by_name["db"].depends_on == ["core"]
    assert sorted(by_name["api"].depends_on) == ["core", "db", "utils"]
    assert by_name["utils"].depends_on == []


def test_load_config_layers(sample_config):
    config = load_config(sample_config)
    assert config.layers.order == ["api", "db", "core", "utils"]


def test_load_config_rules(sample_config):
    config = load_config(sample_config)
    assert config.rules.no_cycles is True
    assert config.rules.enforce_layers is True
    assert config.rules.enforce_depends_on is True
    assert config.rules.exclude_test_files is True


def test_load_missing_config():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/governance.toml")
