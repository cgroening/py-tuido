import logging
import platform
import os
import shutil
import typer
from pathlib import Path
from typing import Annotated, Optional
from termz.util.logger import setup_logging
from termz.io.app_state_storage import AppStateStorage
from tuido import PACKAGE_NAME, APP_TITLE, APP_SUB_TITLE
from tuido.services.config_service  import ConfigService
from tuido.services.tasks_service   import TasksService
from tuido.services.topics_service  import TopicsService
from tuido.services.notes_service   import NotesService
from tuido.storage.config.yaml      import YamlConfigRepository
from tuido.storage.tasks.json       import JsonTaskRepository
from tuido.storage.topics.json      import JsonTopicRepository
from tuido.storage.notes.md         import MarkdownNotesRepository


_BUNDLED_DATA_DIR = Path(__file__).parent.parent / 'sample_data'


# Setup logging and application state storage
setup_logging('tuido')
logger = logging.getLogger(__name__)
logger.info('App is starting...')
_ = AppStateStorage(package_name=PACKAGE_NAME)

#Dependency composition: Wire all layers together
_config_repo = YamlConfigRepository()
_task_repo   = JsonTaskRepository()
_topic_repo  = JsonTopicRepository()
_notes_repo  = MarkdownNotesRepository()

app = typer.Typer(help=f'{APP_TITLE} - {APP_SUB_TITLE}')


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        '-C', '--config',
        metavar='DIR',
        help=(
            'Folder containing config.yaml and bindings.yaml '
            '(default: ~/.config/tuido/ on macOS/Linux, '
            '%APPDATA%\\tuido\\ on Windows)'
        ),
    ),
    data_folder: Annotated[Optional[Path], typer.Option(
        '-D', '--data-folder',
        metavar='DIR',
        help=(
            'Folder containing tasks.json, topics.json, notes.md '
            '(default: ~/.local/share/tuido/ on macOS/Linux, '
            '%LOCALAPPDATA%\\tuido\\ on Windows)'
        ),
    )] = None,
):
    # Resolve config dir
    config_dir = config if config else _get_config_dir()
    _ensure_config_exists(config_dir)

    # Resolve data dir
    data_dir = data_folder if data_folder else _get_data_dir()
    _ensure_data_dir_exists(data_dir)

    # Set paths on repos
    _config_repo.set_path(str(config_dir / 'config.yaml'))
    _task_repo.set_path(str(data_dir / 'tasks.json'))
    _topic_repo.set_path(str(data_dir / 'topics.json'))
    _notes_repo.set_path(str(data_dir / 'notes.md'))

    # Wire services
    config_service  = ConfigService(_config_repo)
    tasks_service   = TasksService(_task_repo, config_service)
    topics_service  = TopicsService(_topic_repo, config_service)
    notes_service   = NotesService(_notes_repo)

    # Init bindings
    from tuido.tui import bindings as _bindings
    _bindings.init(config_dir / 'bindings.yaml')

    from tuido.tui.app import TuidoApp
    if ctx.invoked_subcommand is None:
        TuidoApp(
            config_service, tasks_service, topics_service, notes_service
        ).run()


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


def main() -> None:
    app()
