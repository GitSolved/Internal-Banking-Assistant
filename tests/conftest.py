import os
import pathlib
from glob import glob

import pytest

root_path = pathlib.Path(__file__).parents[1]
# This is to prevent a bug in intellij that uses the wrong working directory
os.chdir(root_path)


def _as_module(fixture_path: str) -> str:
    return fixture_path.replace("/", ".").replace("\\", ".").replace(".py", "")


pytest_plugins = [_as_module(fixture) for fixture in glob("tests/fixtures/[!_]*.py")]


@pytest.fixture(scope="function")
def worker_id(request):
    """Return the ID of the current test worker for parallel test execution."""
    # If running with pytest-xdist, this will be gw0, gw1, etc.
    # Otherwise, it will be "master" (single process)
    return getattr(request.config, "workerinput", {}).get("workerid", "master")
