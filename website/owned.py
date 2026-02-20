import yaml

class Owned:
    def __init__(self, yaml_path: str):
        data = yaml.safe_load(open(yaml_path))
        self._owned = set()

        for item in data["owned"]:
            parts = str(item).split("-")

            start = int(parts[0])
            end = int(parts[1]) if len(parts) > 1 else start

            self._owned.update(range(start, end + 1))

    # permite: collection[105]
    def __getitem__(self, volume: int) -> bool:
        return volume in self._owned

    # permite: 105 in collection
    def __contains__(self, volume: int) -> bool:
        return volume in self._owned

    # caso queira 0/1 direto
    def flag(self, volume: int) -> int:
        return int(volume in self._owned)