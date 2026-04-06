"""Custom exception types for the tuido domain."""


class ConfigNotFoundError(Exception):
    """Raised when the config YAML file is not found."""

    def __init__(self, path: str) -> None:
        super().__init__(f'Config file not found: {path}')


class TopicsFileNotFoundError(Exception):
    """Raised when the topics JSON file is not found."""

    def __init__(self, path: str) -> None:
        super().__init__(f'Topics file not found: {path}')


class TaskNotFoundError(Exception):
    """Raised when a task cannot be located."""

    def __init__(self, column: str, index: int) -> None:
        super().__init__(f'Task not found at column="{column}", index={index}')
