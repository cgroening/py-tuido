from abc import ABC, abstractmethod


class BaseTaskRepository(ABC):
    """
    Interface for task persistence.

    The repository works with raw dicts (JSON-serialisable) to keep
    the storage layer free of domain object construction logic.
    """

    @abstractmethod
    def load_task(self) -> dict[str, list[dict[str, object]]]:
        """
        Loads tasks from the backing store.

        Returns
        -------
        dict[str, list[dict[str, object]]]
            Mapping of column_name → list of raw task dicts with keys:
            description, priority (int), start_date, end_date.
        """
        ...

    @abstractmethod
    def save_task(self, tasks_raw: dict[str, list[dict[str, object]]]) -> None:
        """
        Persists the full tasks dict to the backing store.

        Parameters
        ----------
        tasks_raw : dict[str, list[dict]]
            Mapping of column_name → list of raw task dicts.
        """
        ...
