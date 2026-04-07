from pathlib import Path
from termz.tui.custom_bindings import CustomBindings  # type: ignore

_BINDINGS_FILE = Path(__file__).parent / 'bindings.yaml'
CUSTOM_BINDINGS = CustomBindings(yaml_file=str(_BINDINGS_FILE))
