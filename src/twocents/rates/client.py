from enum import Enum
from typing import Any

import requests

from twocents.utils.pretty_print import print_verbose


class Language(Enum):
    """Enumeration for supported languages."""

    IT = "it"
    EN = "en"


def _check_response_code(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")
        return response

    return wrapper


class RatesClient:
    def __init__(self, language: Language = Language.EN):
        self.base_url = (
            "https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0"
        )
        self.language = language

    def _make_get_request(self, endpoint: str, headers: dict[str, str] | None = None):
        url = f"{self.base_url}/{endpoint}"
        url += f"?lang={self.language.value}"
        print_verbose(f"Making GET request to URL: {url}")
        response = requests.get(url=url, headers=headers)
        print_verbose(f"Received response with status code: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_available_currencies(self) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        return self._make_get_request("currencies", headers=headers)
