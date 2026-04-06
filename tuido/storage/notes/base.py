from abc import ABC, abstractmethod


class BaseNotesRepository(ABC):
    """Interface for notes persistence."""

    @abstractmethod
    def load(self) -> str:
        """Load and return the notes text."""
        ...

    @abstractmethod
    def save(self, text: str) -> None:
        """Persist the notes text."""
        ...
