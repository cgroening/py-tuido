import os
from tuido.storage.notes.base import BaseNotesRepository


class MarkdownNotesRepository(BaseNotesRepository):
    """Persists notes to a Markdown file."""

    _path: str | None


    def __init__(self, md_path: str | None = None) -> None:
        self._path = md_path
        if md_path is not None:
            self.set_path(md_path)

    def set_path(self, md_path: str) -> None:
        """
        Sets the path to the Markdown file and creates it if it doesn't exist.
        """
        self._path = md_path
        if not os.path.exists(self._path):
            with open(self._path, 'w', encoding='utf-8') as f:
                f.write('')

    def load_note_text(self) -> str:
        """Loads and returns the notes text from the Markdown file."""
        if self._path is None:
            return ''
        with open(self._path, 'r', encoding='utf-8') as f:
            return f.read()

    def save_note_text(self, text: str) -> None:
        """Saves the notes text to the Markdown file."""
        if self._path is None:
            return
        with open(self._path, 'w', encoding='utf-8') as f:
            f.write(text)
