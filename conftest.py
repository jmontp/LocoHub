import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="Explicitly enable tests reading full local datasets/native tools")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    import pytest
    skip = pytest.mark.skip(reason="Full-data/native integration checks are opt-in (--run-integration)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
