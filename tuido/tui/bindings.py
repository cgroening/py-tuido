from pathlib import Path
from pylightlib.textual import CustomBindings  # type: ignore

_BINDINGS_FILE = Path(__file__).parent / 'bindings.yaml'
CUSTOM_BINDINGS = CustomBindings(
    yaml_file=str(_BINDINGS_FILE),
    with_copy_paste_keys=True,
)
