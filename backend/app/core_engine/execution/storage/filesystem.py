import json
import shutil


class FileSystemStorage:

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.raw_dir = base_dir / "raw"
        self.normalized_dir = base_dir / "normalized"

    def reset(self):
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
        self.raw_dir.mkdir(parents=True)
        self.normalized_dir.mkdir(parents=True)

    def save_raw(self, raw, name):
        self._save(self.raw_dir / f"{name}.json", raw)

    def save_normalized(self, doc, name):
        self._save(self.normalized_dir / f"{name}.json", doc)

    def _save(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)