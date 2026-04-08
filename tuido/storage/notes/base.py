from abc import ABC, abstractmethod


class BaseNotesRepository(ABC):
    """Interface for notes persistence."""

    @abstractmethod
    def load_note_text(self) -> str:
        """Loads and returns the notes text."""
        ...

    @abstractmethod
    def save_note_text(self, text: str) -> None:
        """Persists the notes text."""
        ...
