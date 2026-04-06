from abc import ABC, abstractmethod
from tuido.domain.models import FieldDefinition


class BaseConfigRepository(ABC):
    """Interface for loading application configuration."""

    @abstractmethod
    def get_fields(self) -> list[list[dict]]:
        """Return the raw field definitions (rows × cols) from the YAML."""
        ...

    @abstractmethod
    def get_columns(self) -> list[FieldDefinition]:
        """Return all field definitions as a flat list."""
        ...

    @abstractmethod
    def get_columns_dict(self) -> dict[str, FieldDefinition]:
        """Return field definitions keyed by field name."""
        ...

    @abstractmethod
    def get_task_column_names(self) -> list[str]:
        """Return the ordered list of kanban column names."""
        ...

    @abstractmethod
    def get_task_column_captions(self) -> dict[str, str]:
        """Return a mapping of column name → display caption."""
        ...
