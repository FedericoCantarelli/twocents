"""Serialise models (rates, currencies) to JSON or CSV."""

import csv
import json
from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar
from typing import TextIO

from twocents.models import Record


class Exporter(ABC):
    """Writes a sequence of records to a text stream or a file."""

    name: ClassVar[str]
    """Format name, as used by the CLI ``--format`` option."""

    @abstractmethod
    def dump(self, records: Sequence[Record], stream: TextIO) -> None:
        """Write ``records`` to an open text stream (e.g. ``sys.stdout``).

        Args:
            records (Sequence[Record]): Rates, currencies, ...
            stream (TextIO): Destination stream.
        """

    def export(self, records: Sequence[Record], path: str | Path) -> None:
        """Write ``records`` to a file, overwriting it.

        Args:
            records (Sequence[Record]): Rates, currencies, ...
            path (str | Path): Destination file; its directory must exist.

        Raises:
            FileNotFoundError: If the parent directory does not exist.
        """
        with open(path, "w", newline="", encoding="utf-8") as f:
            self.dump(records, f)


class JsonExporter(Exporter):
    """Export records as an indented JSON array."""

    name = "json"

    def dump(self, records: Sequence[Record], stream: TextIO) -> None:
        """Write ``records`` as a JSON array of objects."""
        json.dump([r.to_dict() for r in records], stream, indent=4)
        stream.write("\n")


class CsvExporter(Exporter):
    """Export records as CSV, one row per record with a header line."""

    name = "csv"

    def dump(self, records: Sequence[Record], stream: TextIO) -> None:
        """Write ``records`` as CSV. Nothing is written for an empty list."""
        rows = [r.to_row() for r in records]
        if not rows:
            return
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


EXPORTERS: dict[str, type[Exporter]] = {
    cls.name: cls for cls in (JsonExporter, CsvExporter)
}
"""Available exporters, keyed by format name."""
