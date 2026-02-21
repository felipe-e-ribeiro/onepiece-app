import yaml

class Owned:
    def __init__(self, yaml_path: str):
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        self._volumes = set()
        self._databooks = set()

        # Processa Volumes (ex: 1-59)
        for item in data.get("volumes", []):
            parts = str(item).split("-")
            start = int(parts[0])
            end = int(parts[1]) if len(parts) > 1 else start
            self._volumes.update(range(start, end + 1))

        # Processa Databooks (converte para minúsculo para comparação segura)
        for item in data.get("databooks", []):
            self._databooks.add(str(item).lower())

    def __getitem__(self, key) -> bool:
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            return int(key) in self._volumes
        # Se for string (nome do databook), limpa e checa na lista de databooks
        clean_key = str(key).lower().replace(" ", "_")
        return clean_key in self._databooks

    def __contains__(self, key) -> bool:
        return self.__getitem__(key)