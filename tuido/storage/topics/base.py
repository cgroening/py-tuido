from abc import ABC, abstractmethod


class BaseTopicRepository(ABC):
    """Interface for topic persistence."""

    @abstractmethod
    def load(self) -> list[dict]:
        """
        Load all topics from the backing store.

        Returns
        -------
        list[dict]
            List of topic dicts. Each dict has at least an 'id' key.
        """
        ...

    @abstractmethod
    def save(self, topics: list[dict]) -> None:
        """
        Persist the full topics list to the backing store.

        Parameters
        ----------
        topics : list[dict]
            List of topic dicts to persist.
        """
        ...
