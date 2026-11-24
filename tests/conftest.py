"""Shared fixtures for the twocents test suite.

No test touches the network. ``fake_session`` replaces ``requests.Session``
with a recorder that answers per endpoint, so both a ``RatesClient`` built
by the test and the one the CLI builds internally talk to it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from typing import Any

import pytest
import requests
from click.testing import CliRunner

from twocents.client import RatesClient


@dataclass
class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    payload: Any = None
    status_code: int = 200
    text: str = ""

    def json(self) -> Any:
        return self.payload


Handler = dict | FakeResponse | Exception | Callable[[dict], Any]


@dataclass
class FakeSession:
    """Stand-in for ``requests.Session`` that routes by endpoint name.

    Register answers with :meth:`on`. A handler may be a payload dict, a
    ``FakeResponse``, an exception to raise, or a callable taking the query
    params and returning any of those. Unregistered endpoints return ``{}``.
    """

    handlers: dict[str, Handler] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def on(self, endpoint: str, handler: Handler) -> "FakeSession":
        self.handlers[endpoint] = handler
        return self

    def get(self, url: str, params=None, headers=None, timeout=None):
        endpoint = url.rsplit("/", 1)[-1]
        params = dict(params or {})
        self.calls.append(
            {
                "url": url,
                "endpoint": endpoint,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        handler = self.handlers.get(endpoint, {})
        if callable(handler) and not isinstance(handler, FakeResponse):
            handler = handler(params)
        if isinstance(handler, Exception):
            raise handler
        if isinstance(handler, FakeResponse):
            return handler
        return FakeResponse(payload=handler)

    @property
    def endpoints(self) -> list[str]:
        return [c["endpoint"] for c in self.calls]


@pytest.fixture
def fake_session(monkeypatch) -> FakeSession:
    session = FakeSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    return session


@pytest.fixture
def client(fake_session) -> RatesClient:
    return RatesClient()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
