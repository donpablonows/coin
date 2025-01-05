"""Pytest configuration for Coin test suite."""

import pytest
import os
import tempfile
import shutil

@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)

@pytest.fixture(scope="session")
def cuda_available():
    """Check if CUDA is available."""
    try:
        import numba.cuda
        return numba.cuda.is_available()
    except ImportError:
        return False

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "cuda: mark test as requiring CUDA capability"
    )

def pytest_collection_modifyitems(config, items):
    """Skip CUDA tests if CUDA is not available."""
    if not pytest.config.getoption("--run-cuda"):
        skip_cuda = pytest.mark.skip(reason="need --run-cuda option to run")
        for item in items:
            if "cuda" in item.keywords:
                item.add_marker(skip_cuda)

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--run-cuda",
        action="store_true",
        default=False,
        help="run tests that require CUDA"
    ) 