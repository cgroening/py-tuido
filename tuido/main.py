import logging
import platform
import os
import shutil
import typer
from pathlib import Path
from typing import Annotated, Optional
from termz.util.logger import setup_logging
from termz.io.app_state_storage import AppStateStorage
from tuido import PACKAGE_NAME


_BUNDLED_DATA_DIR = Path(__file__).parent.parent / 'sample_data'


# Setup logging and application state storage
setup_logging('termplate')
logger = logging.getLogger(__name__)
logger.info('App is starting...')
_ = AppStateStorage(package_name=PACKAGE_NAME)


def _get_config_dir() -> Path:
    """Returns the platform-appropriate user config directory."""
    if platform.system() == 'Windows':
        base = Path(os.environ.get('APPDATA', Path.home()))
    else:
        base = Path.home() / '.config'
    return base / PACKAGE_NAME


def _get_data_dir() -> Path:
    """Returns the platform-appropriate user data directory."""
    if platform.system() == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    else:
        base = Path.home() / '.local' / 'share'
    return base / PACKAGE_NAME


def _ensure_config_exists(config_dir: Path) -> None:
    """Copy bundled default config files to user config dir on first run."""
    config_dir.mkdir(parents=True, exist_ok=True)
    for filename in ('config.yaml', 'bindings.yaml'):
        dest = config_dir / filename
        if not dest.exists():
            shutil.copy(_BUNDLED_DATA_DIR / filename, dest)


def _ensure_data_dir_exists(data_dir: Path) -> None:
    """Create data directory and copy default empty files on first run."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename in ('tasks.json', 'topics.json', 'notes.md'):
        dest = data_dir / filename
        if not dest.exists():
            shutil.copy(_BUNDLED_DATA_DIR / filename, dest)


_app = typer.Typer(name=PACKAGE_NAME, add_completion=False)


@_app.command()
def _run(
    config: Annotated[Optional[Path], typer.Option(
        '-C', '--config',
        metavar='DIR',
        help=(
            'Folder containing config.yaml and bindings.yaml '
            '(default: ~/.config/tuido/ on macOS/Linux, '
            '%APPDATA%\\tuido\\ on Windows)'
        ),
    )] = None,
    data_folder: Annotated[Optional[Path], typer.Option(
        '-D', '--data-folder',
        metavar='DIR',
        help=(
            'Folder containing tasks.json, topics.json, notes.md '
            '(default: ~/.local/share/tuido/ on macOS/Linux, '
            '%LOCALAPPDATA%\\tuido\\ on Windows)'
        ),
    )] = None,
) -> None:
    setup_logging(PACKAGE_NAME)

    # --- Resolve config dir ---
    if config:
        config_dir = config
    else:
        config_dir = _get_config_dir()
        _ensure_config_exists(config_dir)
    config_path = config_dir / 'config.yaml'

    # --- Resolve data dir ---
    if data_folder:
        data_dir = data_folder
    else:
        data_dir = _get_data_dir()
        _ensure_data_dir_exists(data_dir)

    # --- Storage layer ---
    from tuido.storage.config.yaml import YamlConfigRepository
    from tuido.storage.tasks.json  import JsonTaskRepository
    from tuido.storage.topics.json_ import JsonTopicRepository
    from tuido.storage.notes.md     import MarkdownNotesRepository

    config_repo = YamlConfigRepository(str(config_path))
    task_repo   = JsonTaskRepository(str(data_dir / 'tasks.json'))
    topic_repo  = JsonTopicRepository(str(data_dir / 'topics.json'))
    notes_repo  = MarkdownNotesRepository(str(data_dir / 'notes.md'))

    # --- Service layer ---
    from tuido.services.config_service  import ConfigService
    from tuido.services.tasks_service   import TasksService
    from tuido.services.topics_service  import TopicsService
    from tuido.services.notes_service   import NotesService

    config_service  = ConfigService(config_repo)
    tasks_service   = TasksService(task_repo, config_service)
    topics_service  = TopicsService(topic_repo, config_service)
    notes_service   = NotesService(notes_repo)

    # --- Bindings ---
    from tuido.tui import bindings as _bindings
    _bindings.init(config_path.parent / 'bindings.yaml')

    # --- TUI layer ---
    from tuido.tui.app import TuidoApp

    TuidoApp(config_service, tasks_service, topics_service, notes_service).run()


def main() -> None:
    _app()


if __name__ == '__main__':
    main()
