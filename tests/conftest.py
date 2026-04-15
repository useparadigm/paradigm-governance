from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"
SAMPLE_CONFIG = SAMPLE_PROJECT / "governance.toml"
TRANSITIVE_PROJECT = FIXTURES_DIR / "transitive_project"
TRANSITIVE_CONFIG = TRANSITIVE_PROJECT / "governance.toml"
SAMPLE_TS_PROJECT = FIXTURES_DIR / "sample_ts_project"
SAMPLE_TS_CONFIG = SAMPLE_TS_PROJECT / "governance.toml"


@pytest.fixture
def sample_project():
    return SAMPLE_PROJECT


@pytest.fixture
def sample_config():
    return SAMPLE_CONFIG


@pytest.fixture
def transitive_config():
    return TRANSITIVE_CONFIG


@pytest.fixture
def sample_ts_project():
    return SAMPLE_TS_PROJECT


@pytest.fixture
def sample_ts_config():
    return SAMPLE_TS_CONFIG
