"""Tests for the library's public surface and its independence from click."""

import subprocess
import sys

import twocents


def test_public_api_is_importable():
    for name in twocents.__all__:
        assert hasattr(twocents, name), name


def test_importing_library_does_not_import_click():
    code = "import sys, twocents; sys.exit('click' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], check=False)
    assert result.returncode == 0


def test_library_does_not_configure_logging():
    import logging

    handlers = logging.getLogger("twocents").handlers
    assert all(isinstance(h, logging.NullHandler) for h in handlers)
