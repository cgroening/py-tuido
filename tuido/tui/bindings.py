from pathlib import Path
from termz.tui.custom_bindings import CustomBindings

_PARENT_FOLDER = Path(__file__).parent.parent.parent
_BUNDLED_BINDINGS_FILE_PATH = _PARENT_FOLDER / 'sample_data' / 'bindings.yaml'
custom_bindings = CustomBindings(yaml_file=str(_BUNDLED_BINDINGS_FILE_PATH))


def init(path: Path) -> None:
    """Re-initializes CUSTOM_BINDINGS from a user-supplied path."""
    global custom_bindings
    custom_bindings = CustomBindings(yaml_file=str(path))
