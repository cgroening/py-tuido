"""
Composition root for the Tuido application.

Wires all layers together (storage → services → TUI) and launches
the Textual app. This is the only place where concrete implementations
are instantiated; every other module depends on abstractions.
"""
import argparse
import platform
import os
import shutil
from pathlib import Path

from termz.util.logger import setup_logging  # type: ignore

from tuido import PACKAGE_NAME


_BUNDLED_CONFIG = Path(__file__).parent / 'data' / 'config.yaml'


def _get_config_dir() -> Path:
    """Returns the platform-appropriate user config directory."""
    if platform.system() == 'Windows':
        base = Path(os.environ.get('APPDATA', Path.home()))
    else:
        base = Path.home() / '.config'
    return base / PACKAGE_NAME


def _ensure_config_exists(config_path: Path) -> None:
    """Copy bundled default config to user config dir on first run."""
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_BUNDLED_CONFIG, config_path)


def main() -> None:
    setup_logging(PACKAGE_NAME)

    # --- Parse arguments ---
    parser = argparse.ArgumentParser(prog=PACKAGE_NAME)
    parser.add_argument(
        '-C', '--config', type=str, default=None,
        metavar='PATH',
        help=(
            'Path to config.yaml '
            '(default: ~/.config/tuido/config.yaml on macOS/Linux, '
            '%%APPDATA%%\\tuido\\config.yaml on Windows)'
        ),
    )
    parser.add_argument(
        '--data_folder', type=str, default='data',
        metavar='DIR',
        help='Folder containing tasks.json, topics.json, notes.md (default: data/)',
    )
    args = parser.parse_args()

    # --- Resolve config path ---
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = _get_config_dir() / 'config.yaml'
        _ensure_config_exists(config_path)

    # --- Resolve data dir ---
    data_dir = Path(__file__).parent.parent / args.data_folder

    # --- Storage layer ---
    from tuido.storage.config.yaml_ import YamlConfigRepository
    from tuido.storage.tasks.json_  import JsonTaskRepository
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

    # --- TUI layer ---
    from tuido.tui.app import TuidoApp

    TuidoApp(config_service, tasks_service, topics_service, notes_service).run()


if __name__ == '__main__':
    main()
