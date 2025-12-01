import os

from pylightlib.msc.Singleton import Singleton  # type: ignore


class Notes(metaclass=Singleton):
    """
    Model for the notes tab.

    Attributes
    ----------
    md_path : str
        The path to the Markdown file containing the notes.
    notes : str
        The content of the notes.
    """
    md_path: str
    notes: str

    def __init__(self, md_path: str):
        """
        Initializes the Notes model.

        Parameters
        ----------
        md_path : str
            The path to the Markdown file containing the notes.
        """
        self.md_path = md_path
        self.load_from_file()

    def load_from_file(self):
        """
        Loads the notes from a Markdown file.

        If the file does not exist, it creates an empty file.
        """
        # Create the file if it does not exist
        if not os.path.exists(self.md_path):
            with open(self.md_path, 'w', encoding='utf-8') as file:
                file.write('')

        # Load the notes from the file
        with open(self.md_path, 'r', encoding='utf-8') as file:
            self.notes = file.read()

    def save_to_file(self):
        """
        Saves the notes to the Markdown file.
        """
        with open(self.md_path, 'w', encoding='utf-8') as file:
            file.write(self.notes)
