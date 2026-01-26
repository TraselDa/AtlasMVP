from pathlib import Path
import json


class ConfigNotFoundError(Exception):
    pass


class ConfigResolver:
    def __init__(self, registry: dict):
        self.registry = registry

    def resolve(self, normalized_doc: dict) -> dict:
        source_type = normalized_doc.get("source_type")

        if not source_type:
            raise ValueError("normalized document has no source_type")

        if source_type not in self.registry:
            raise ConfigNotFoundError(
                f"No config registered for source_type='{source_type}'"
            )

        config_path = Path(self.registry[source_type])

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)