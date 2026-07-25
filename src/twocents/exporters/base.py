from abc import ABC
from abc import abstractmethod
from pathlib import Path


class Exporter(ABC):
    """Interface for Exporters class.

    The interface defines the methods that any exporter class should implement.

    Methods:
        export(file_path: Path | str): Export the data to a file.
    """

    def __init__(self, data: list[dict[str, str]]):
        """Init Exporter class.

        It take as input a list of dictionaries, where each dictionary
        represents a row of data to be exported. In case the output format
        requires an header row, the concrete class should handle it.

        Args:
            data (list[dict[str, str]]): The data to be exported.
        """
        self.data = data

    @abstractmethod
    def export(self, file_path: Path | str):
        """Export the data to a file or to an out channel.

        Args:
            file_path (Path | str): The path to the file or the channel.
        """
