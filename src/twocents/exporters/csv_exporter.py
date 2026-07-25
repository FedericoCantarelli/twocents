from pathlib import Path

import click

from twocents.exporters.base import Exporter


class CsvExporter(Exporter):
    """Exporter class for exporting data in CSV format."""

    def export(self, file_path: str | Path):
        """Export the data to a csv file.

        Args:
            file_path (str | Path): The path to the CSV file.
        """
        import csv

        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.parent.exists():
            raise click.BadParameter(
                f"The directory {file_path.parent} does not exist."
            )

        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.data[0].keys())
            writer.writeheader()
            writer.writerows(self.data)
