import logging
import threading
import time
from tuido.storage.notes.base import BaseNotesRepository


class NotesService:
    """
    Service for notes management with throttle/debounce auto-save.

    The service holds the current text in memory and saves it to the
    repository with two complementary mechanisms:

    - **Throttle:** saves at most once per `THROTTLE_INTERVAL` seconds
      while the user is actively typing.
    - **Debounce:** saves once the user has stopped typing for
      `DEBOUNCE_INTERVAL` seconds.
    """

    THROTTLE_INTERVAL: float = 5.0
    DEBOUNCE_INTERVAL: float = 5.0

    _repo: BaseNotesRepository
    _notes: str
    _last_throttle: float
    _debounce_timer: threading.Timer | None
    _lock: threading.Lock


    def __init__(self, repo: BaseNotesRepository) -> None:
        self._repo = repo
        self._notes = repo.load_note_text()
        self._last_throttle = 0.0
        self._debounce_timer = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Reload notes from the repository."""
        self._notes = self._repo.load_note_text()

    def get_notes(self) -> str:
        """Return the current in-memory notes text."""
        return self._notes

    def on_text_changed(self, text: str) -> None:
        """
        Called whenever the notes textarea content changes.

        Applies throttle and debounce logic and saves asynchronously.
        """
        now = time.time()

        if now - self._last_throttle >= self.THROTTLE_INTERVAL:
            self._save(text, 'throttle')
            self._last_throttle = now

        if self._debounce_timer:
            self._debounce_timer.cancel()

        self._debounce_timer = threading.Timer(
            self.DEBOUNCE_INTERVAL, self._save, args=(text, 'debounce')
        )
        self._debounce_timer.start()

    def _save(self, text: str, reason: str) -> None:
        if self._notes != text:
            self._notes = text
            self._repo.save_note_text(text)
            logging.info(
                f'[{time.strftime("%X")}] [{reason}] Notes saved.'
            )
