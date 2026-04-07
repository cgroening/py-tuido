import logging
import platform
import os
import shutil
import typer
from pathlib import Path
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
_config_dir: Path
_data_dir: Path


# Setup logging and application state storage
setup_logging('tuido')
logger = logging.getLogger(__name__)
logger.info('App is starting...')
_ = AppStateStorage(package_name=PACKAGE_NAME)

# Dependency composition: Wire all layers together
_config_repo    = YamlConfigRepository()
_config_service = ConfigService(_config_repo)
_task_repo      = JsonTaskRepository()
_tasks_service  = TasksService(_task_repo, _config_service)
_topic_repo     = JsonTopicRepository()
_topics_service = TopicsService(_topic_repo, _config_service)
_notes_repo     = MarkdownNotesRepository()
_notes_service  = NotesService(_notes_repo)

app = typer.Typer(help=f'{APP_TITLE} - {APP_SUB_TITLE}')


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    custom_config_dir: Path | None = typer.Option(
        None,
        '-C', '--config',
        metavar='DIR',
        help=(
            'Folder containing config.yaml and bindings.yaml '
            '(default: ~/.config/tuido/ on macOS/Linux, '
            '%APPDATA%\\tuido\\ on Windows)'
        ),
    ),
    custom_data_dir: Path | None = typer.Option(
        '-D', '--data-folder',
        metavar='DIR',
        help=(
            'Folder containing tasks.json, topics.json, notes.md '
            '(default: ~/.local/share/tuido/ on macOS/Linux, '
            '%LOCALAPPDATA%\\tuido\\ on Windows)'
        ),
    )
):
    _resolve_config_and_data_dirs(custom_config_dir, custom_data_dir)
    _set_repo_paths()
    _reload_services()

    # Start the TUI if no subcommand was invoked
    if ctx.invoked_subcommand is None:
        _start_tui()


def _resolve_config_and_data_dirs(
    custom_config_dir: Path | None, custom_data_dir: Path | None
) -> None:
    """
    Determines config and data directories, create them if they don't exist
    and copy default files on first run.
    """
    global _config_dir, _data_dir

    _config_dir = custom_config_dir if custom_config_dir else _get_config_dir()
    _ensure_config_exists(_config_dir)

    _data_dir = custom_data_dir if custom_data_dir else _get_data_dir()
    _ensure_data_dir_exists(_data_dir)


def _set_repo_paths() -> None:
    """
    Sets the resolved config and data paths on the repositories.
    """
    _config_repo.set_path(str(_config_dir / 'config.yaml'))
    _task_repo.set_path(str(_data_dir / 'tasks.json'))
    _topic_repo.set_path(str(_data_dir / 'topics.json'))
    _notes_repo.set_path(str(_data_dir / 'notes.md'))

def _reload_services() -> None:
    """
    Reloads all services, e.g. after config changes.
    """
    _tasks_service.load()
    _topics_service.load()
    _notes_service.load()


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


def _start_tui() -> None:
    """Initialize TUI bindings and start the app."""
    from tuido.tui import bindings as _bindings
    from tuido.tui.app import TuidoApp

    _bindings.init(_config_dir / 'bindings.yaml')
    TuidoApp(
        _config_service, _tasks_service, _topics_service, _notes_service
    ).run()


def main() -> None:
    app()
