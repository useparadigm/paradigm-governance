from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"
SAMPLE_CONFIG = SAMPLE_PROJECT / "governance.toml"


@pytest.fixture
def sample_project():
    return SAMPLE_PROJECT


@pytest.fixture
def sample_config():
    return SAMPLE_CONFIG
