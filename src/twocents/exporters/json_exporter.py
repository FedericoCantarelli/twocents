class JsonExporter:
    def __init__(self, data):
        self.data = data

    def export(self, file_path):
        import json

        with open(file_path, "w") as f:
            json.dump(self.data, f, indent=4)
