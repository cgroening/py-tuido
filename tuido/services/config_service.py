from tuido.domain.models import FieldDefinition
from tuido.storage.config.base import BaseConfigRepository


class ConfigService:
    """
    Provides access to the application configuration.

    Wraps the config repository and exposes config data to other
    service and TUI layers without them knowing about the storage
    implementation.
    """

    _repo: BaseConfigRepository


    def __init__(self, repo: BaseConfigRepository) -> None:
        self._repo = repo

    def get_fields(self) -> list[list[dict]]:
        """Return the raw field definitions (rows × cols) for the topics form."""
        return self._repo.get_fields()

    def get_columns(self) -> list[FieldDefinition]:
        """Return all field definitions as a flat list."""
        return self._repo.get_columns()

    def get_columns_dict(self) -> dict[str, FieldDefinition]:
        """Return field definitions keyed by field name."""
        return self._repo.get_columns_dict()

    def get_task_column_names(self) -> list[str]:
        """Return the ordered list of kanban column names."""
        return self._repo.get_task_column_names()

    def get_task_column_captions(self) -> dict[str, str]:
        """Return a mapping of column name → display caption."""
        return self._repo.get_task_column_captions()
