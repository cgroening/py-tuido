import logging
import threading
import time
from time import sleep

from textual import on
from textual.widgets import TextArea

from pylightlib.msc.Singleton import Singleton  # type: ignore

from model.config_model import Config  # type: ignore
from model.notes_model import Notes    # type: ignore
from view.main_view import MainTabs  # type: ignore


class NotesController(metaclass=Singleton):
    """
    Controller for the Notes tab in the application.

    This class handles the interaction between the Notes model and the UI.
    It implements a throttle and debounce mechanism to optimize performance
    when the user types in the TextArea.

    Attributes
    ----------
    config : Config
        The configuration object.
    notes_model : Notes
        The notes model object.
    main_tabs : MainTabs
        The main tabs object.
    throttle_interval : float
        Time interval for the throttle mechanism.
    debounce_interval : float
        Time interval for the debounce mechanism.
    last_throttle_call : float
        Timestamp of the last throttle call.
    latest_text : str
        The latest text entered in the TextArea.
    throttle_lock : threading.Lock
        A threading lock for thread-safe operations.
    debounce_timer : threading.Timer | None
        A timer for the debounce mechanism.
    """
    config: Config
    notes_model: Notes
    main_tabs: MainTabs
    throttle_interval: float = 5.0
    debounce_interval: float = 5.0
    last_throttle_call: float = 0.0
    throttle_lock = threading.Lock()
    debounce_timer: threading.Timer | None = None


    def __init__(self, config: Config, notes_model: Notes, main_tabs: MainTabs):
        """
        Initializes the NotesController.

        Parameters
        ----------
        config : Config
            The configuration object.
        notes_model : Notes
            The notes model object.
        main_tabs : MainTabs
            The main tabs object.
        """
        self.config = config
        self.notes_model = notes_model
        self.main_tabs = main_tabs

        self.setup_textarea()

    def setup_textarea(self) -> None:
        """
        Sets the text from the markdown file and the event handler for the
        TextArea in the Notes tab.
        """
        notes_tab = self.main_tabs.notes_tab
        textarea: TextArea = notes_tab.textarea
        textarea.text = self.notes_model.notes
        notes_tab.text_area_changed_action = self.text_area_changed_action


    def text_area_changed_action(self, text: str) -> None:
        """
        Handles the text area change event.

        This method implements a throttle and debounce mechanism to optimize
        performance when the user types in the TextArea.
        The throttle mechanism ensures that the text is saved only after a
        certain interval of time has passed since the last save.
        The debounce mechanism ensures that the text is finally saved after the
        user has stopped typing for a certain interval of time.

        Parameters
        ----------
        text : str
            The text entered in the TextArea.
        """
        now = time.time()

        # Throttle: Save the text only if the throttle interval has passed
        if now - self.last_throttle_call >= self.throttle_interval:
            self.save_text(text, 'throttle')
            self.last_throttle_call = now

        # Debounce: Reset the timer
        if self.debounce_timer:
            self.debounce_timer.cancel()

        # Debounce: Start the timer, action after X seconds
        self.debounce_timer = threading.Timer(
            self.debounce_interval, self.save_text, args=(text, 'debounce')
        )
        self.debounce_timer.start()

    def save_text(self, text: str, reason: str) -> None:
        """
        Saves the text to the notes model.

        This method is called when the user types in the TextArea.

        Parameters
        ----------
        text : str
            The text entered in the TextArea.
        reason : str
            The reason for saving the text ("throttle" or "debounce").
        """
        if self.notes_model.notes != text:
            self.notes_model.notes = text
            self.notes_model.save_to_file()
            logging.info(f'[{time.strftime('%X')}] [{reason}] Saved note')
