import json
from typing import Any


class StdOutExporter:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    def export(self):
        print(json.dumps(self.data, indent=4))  # noqa: T201
