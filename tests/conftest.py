import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.fakes import FakePlugin, FakeWebSocket, redirect_log_files  # noqa: E402

redirect_log_files()


@pytest.fixture
def ws():
    return FakeWebSocket()


@pytest.fixture
def plugin(ws):
    return FakePlugin(ws)
