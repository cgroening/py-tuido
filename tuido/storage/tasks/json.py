import json
import os
from tuido.storage.tasks.base import BaseTaskRepository


class JsonTaskRepository(BaseTaskRepository):
    """Persists tasks to a JSON file."""

    _path: str


    def __init__(self, json_path: str | None = None) -> None:
        self._path = json_path
        if json_path is not None:
            self.set_path(json_path)

    def set_path(self, json_path: str) -> None:
        self._path = json_path
        if not os.path.exists(self._path):
            with open(self._path, 'w', encoding='utf-8') as f:
                f.write('{}')

    def load(self) -> dict[str, list[dict]]:
        if self._path is None:
            return {}
        with open(self._path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)

    def save(self, tasks_raw: dict[str, list[dict]]) -> None:
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(tasks_raw, f, indent=4)
