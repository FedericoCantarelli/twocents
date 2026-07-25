from pathlib import Path

import click

from twocents.exporters.base import Exporter


class JsonExporter(Exporter):
    """Exporter class for exporting data in JSON format."""

    def export(self, file_path: str | Path):
        """Export the data to a json file.

        Args:
            file_path (str | Path): The path to the JSON file.
        """
        import json

        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.parent.exists():
            raise click.BadParameter(
                f"The directory {file_path.parent} does not exist."
            )

        with open(file_path, "w") as f:
            json.dump(self.data, f, indent=4)
