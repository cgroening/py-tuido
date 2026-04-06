"""
Composition root for the Tuido application.

Wires all layers together (storage → services → TUI) and launches
the Textual app. This is the only place where concrete implementations
are instantiated; every other module depends on abstractions.
"""
import argparse
import logging
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.parent
LOG_DIR    = SCRIPT_DIR / 'log'
LOG_FILE   = LOG_DIR / 'info.log'


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        filemode='w',
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )


def main() -> None:
    _setup_logging()

    # --- Parse optional --data_folder argument ---
    parser = argparse.ArgumentParser(prog='tuido')
    parser.add_argument(
        '--data_folder', type=str, default='data',
        help='Folder containing config.yaml, tasks.json, topics.json, notes.md'
    )
    args = parser.parse_args()
    data_dir = SCRIPT_DIR / args.data_folder

    # --- Storage layer ---
    from tuido.storage.config.yaml_ import YamlConfigRepository
    from tuido.storage.tasks.json_  import JsonTaskRepository
    from tuido.storage.topics.json_ import JsonTopicRepository
    from tuido.storage.notes.md     import MarkdownNotesRepository

    config_repo = YamlConfigRepository(str(data_dir / 'config.yaml'))
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

    app = TuidoApp(config_service, tasks_service, topics_service, notes_service)
    app.run()


if __name__ == '__main__':
    main()
