import json


class StdOutExporter:
    """Exporter class for exporting data to stdout."""

    def __init__(self, data: list[dict[str, str]]):
        """Init Exporter class.

        It take as input a list of dictionaries and print it to stdout.
        This is the default Exporter.

        Args:
            data (list[dict[str, str]]): The data to be exported.
        """
        self.data = data

    def export(self):
        """Export the data to stdout or to a file-like object."""
        import click

        click.echo(json.dumps(self.data, indent=4))
