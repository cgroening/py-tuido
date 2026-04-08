from abc import ABC, abstractmethod


class BaseTopicRepository(ABC):
    """Interface for topic persistence."""

    @abstractmethod
    def load_topics(self) -> list[dict[str, object]]:
        """
        Loads all topics from the backing store.

        Returns
        -------
        list[dict[str, object]]
            List of topic dicts. Each dict has at least an 'id' key.
        """
        ...

    @abstractmethod
    def save_topics(self, topics: list[dict[str, object]]) -> None:
        """
        Persists the full topics list to the backing store.

        Parameters
        ----------
        topics : list[dict[str, object]]
            List of topic dicts to persist.
        """
        ...
