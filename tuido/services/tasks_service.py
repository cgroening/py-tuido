import logging
from datetime import datetime

from termz.util.datetime import (  # type: ignore
    date_to_timestamp, date_diff, today_timestamp
)

from tuido.domain.models import Task, TaskPriority
from tuido.services.config_service import ConfigService
from tuido.storage.tasks.base import BaseTaskRepository


class TasksService:
    """
    Business logic for task management.

    Owns the in-memory task store (dict[column_name, list[Task]]) and
    delegates persistence to the injected repository.
    """

    _repo: BaseTaskRepository
    _config: ConfigService
    _tasks: dict[str, list[Task]]
    _column_names: list[str]
    _column_captions: dict[str, str]


    def __init__(
        self, repo: BaseTaskRepository, config: ConfigService
    ) -> None:
        self._repo = repo
        self._config = config
        self._column_names = config.get_task_column_names()
        self._column_captions = config.get_task_column_captions()
        self._tasks = {}
        self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Re-read config and reload tasks from the repository."""
        self._column_names = self._config.get_task_column_names()
        self._column_captions = self._config.get_task_column_captions()
        self._tasks = {}
        self._load()

    def get_tasks(self) -> dict[str, list[Task]]:
        """Return the in-memory task store."""
        return self._tasks

    def get_column_names(self) -> list[str]:
        return self._column_names

    def get_column_captions(self) -> dict[str, str]:
        return self._column_captions

    def add_task(
        self, column_name: str, task_raw: dict[str, str]
    ) -> tuple[Task, int]:
        """
        Add a new task to the given column.

        Parameters
        ----------
        column_name : str
            Target column name.
        task_raw : dict
            Raw task data with keys: description, priority (str), start_date, end_date.

        Returns
        -------
        tuple[Task, int]
            The new Task object and its index after sorting.
        """
        task = self._create_task(column_name, task_raw)
        if column_name not in self._tasks:
            self._tasks[column_name] = []
        self._tasks[column_name].append(task)
        self._sort_column(column_name)
        self._save()
        index = self._find_task_index(column_name, task)
        return task, index

    def update_task(
        self,
        column_name: str,
        task_index: int,
        task_raw: dict[str, str],
    ) -> tuple[Task, int]:
        """
        Replace an existing task with updated data.

        Returns the updated Task and its new index after sorting.
        """
        self._delete_from_memory(column_name, task_index)
        return self.add_task(column_name, task_raw)

    def delete_task(self, column_name: str, task_index: int) -> None:
        """Remove a task by column name and index."""
        self._delete_from_memory(column_name, task_index)
        self._save()

    def move_task(
        self, source_col: str, task_index: int, target_col: str
    ) -> tuple[Task, int]:
        """
        Move a task from one column to another.

        Returns the moved Task and its new index in the target column.
        """
        task = self._tasks[source_col][task_index]
        self._delete_from_memory(source_col, task_index)
        task.column_name = target_col
        if target_col not in self._tasks:
            self._tasks[target_col] = []
        self._tasks[target_col].append(task)
        self._sort_tasks()
        self._save()
        new_index = self._find_task_index(target_col, task)
        return task, new_index

    # ------------------------------------------------------------------ #
    #  Priority / date helpers (used by TUI layer)                        #
    # ------------------------------------------------------------------ #

    def num_to_priority(self, priority_number: int) -> TaskPriority:
        match priority_number:
            case 1: return TaskPriority.HIGH
            case 2: return TaskPriority.MEDIUM
            case 3: return TaskPriority.LOW
            case _: return TaskPriority.NONE

    def priority_str_to_num(self, priority_string: str) -> int:
        match str(priority_string).upper():
            case 'HIGH':   return 1
            case 'MEDIUM': return 2
            case 'LOW':    return 3
            case _:        return 4

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        raw = self._repo.load()
        for column_name, tasks_list in raw.items():
            self._tasks[column_name] = []
            for task_dict in tasks_list:
                task = self._create_task(column_name, task_dict)
                self._tasks[column_name].append(task)
        self._sort_tasks()
        logging.info(f'TasksService: loaded {sum(len(v) for v in self._tasks.values())} tasks.')

    def _save(self) -> None:
        self._sort_tasks()
        cleaned: dict[str, list[dict]] = {}
        for col, tasks in self._tasks.items():
            cleaned[col] = [
                {
                    'description': t.description,
                    'priority':    t.priority.value,
                    'start_date':  t.start_date,
                    'end_date':    t.end_date,
                }
                for t in tasks
            ]
        self._repo.save(cleaned)
        logging.info('TasksService: tasks saved.')

    def _create_task(
        self, column_name: str, task_dict: dict[str, str]
    ) -> Task:
        return Task(
            column_name  = column_name,
            description  = task_dict['description'],
            priority     = self.num_to_priority(
                               int(task_dict.get('priority', 4))
                           ),
            start_date   = task_dict.get('start_date', ''),
            end_date     = task_dict.get('end_date', ''),
            days_to_start= self._days_to(task_dict.get('start_date', '')),
            days_to_end  = self._days_to(task_dict.get('end_date', '')),
        )

    def _delete_from_memory(
        self, column_name: str, task_index: int
    ) -> None:
        if column_name in self._tasks \
        and 0 <= task_index < len(self._tasks[column_name]):
            del self._tasks[column_name][task_index]

    def _find_task_index(self, column_name: str, task: Task) -> int:
        tasks = self._tasks.get(column_name, [])
        for i, t in enumerate(tasks):
            if t is task:
                return i
        return 0

    def _sort_tasks(self) -> None:
        for col in self._tasks:
            self._sort_column(col)

    def _sort_column(self, column_name: str) -> None:
        MAX_DATE = datetime(3000, 1, 1).timestamp()
        self._tasks[column_name].sort(key=lambda t: (
            t.priority.value,
            date_to_timestamp(t.start_date, english_format=True) or MAX_DATE,
            date_to_timestamp(t.end_date,   english_format=True) or MAX_DATE,
            t.description.lower()
        ))

    @staticmethod
    def _days_to(date_str: str) -> int | None:
        ts = date_to_timestamp(date_str, english_format=True)
        if ts:
            return date_diff(ts, today_timestamp())
        return None
