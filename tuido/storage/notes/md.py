import os
from tuido.storage.notes.base import BaseNotesRepository


class MarkdownNotesRepository(BaseNotesRepository):
    """Persists notes to a Markdown file."""

    _path: str


    def __init__(self, md_path: str | None = None) -> None:
        self._path = md_path
        if md_path is not None:
            self.set_path(md_path)

    def set_path(self, md_path: str) -> None:
        self._path = md_path
        if not os.path.exists(self._path):
            with open(self._path, 'w', encoding='utf-8') as f:
                f.write('')

    def load(self) -> str:
        if self._path is None:
            return ''
        with open(self._path, 'r', encoding='utf-8') as f:
            return f.read()

    def save(self, text: str) -> None:
        with open(self._path, 'w', encoding='utf-8') as f:
            f.write(text)
