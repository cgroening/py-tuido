import json
import os
from tuido.domain.errors import TopicsFileNotFoundError
from tuido.storage.topics.base import BaseTopicRepository


class JsonTopicRepository(BaseTopicRepository):
    """Persists topics to a JSON file."""

    _path: str | None


    def __init__(self, json_path: str | None = None) -> None:
        self._path = json_path
        if json_path is not None:
            self.set_path(json_path)

    def set_path(self, json_path: str) -> None:
        """Sets the path to the JSON file and checks if it exists."""
        self._path = json_path
        if not os.path.exists(self._path):
            raise TopicsFileNotFoundError(self._path)

    def load_topics(self) -> list[dict[str, object]]:
        """Loads and returns the list of topics from the JSON file."""
        if self._path is None:
            return []
        with open(self._path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_topics(self, topics: list[dict[str, object]]) -> None:
        """Saves the full list of topics to the JSON file."""
        if self._path is None:
            return
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(topics, f, indent=4)
