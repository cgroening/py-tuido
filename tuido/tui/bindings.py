from pathlib import Path
from termz.tui.custom_bindings import CustomBindings  # type: ignore

_BUNDLED_BINDINGS = Path(__file__).parent.parent / 'sample_data' / 'bindings.yaml'
CUSTOM_BINDINGS = CustomBindings(yaml_file=str(_BUNDLED_BINDINGS))


def init(path: Path) -> None:
    """Re-initialise CUSTOM_BINDINGS from a user-supplied path."""
    global CUSTOM_BINDINGS
    CUSTOM_BINDINGS = CustomBindings(yaml_file=str(path))
