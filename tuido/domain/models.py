import enum
from dataclasses import dataclass
from enum import Enum, auto


class FieldType(Enum):
    """Field types for the topics form."""
    STRING = auto()
    NUMBER = auto()
    SELECT = auto()
    DATE = auto()


class TaskPriority(enum.Enum):
    """Priority levels for tasks."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    NONE = 4


@dataclass(slots=True)
class Task:
    """
    Domain model for a task.

    Attributes
    ----------
    column_name : str
        The kanban column the task belongs to.
    description : str
        The task description.
    priority : TaskPriority
        The task priority level.
    start_date : str
        Start date in "YYYY-MM-DD" format (empty string if not set).
    end_date : str
        End date in "YYYY-MM-DD" format (empty string if not set).
    days_to_start : int | None
        Days until start date (negative = past, None = not set).
    days_to_end : int | None
        Days until end date (negative = past, None = not set).
    """
    column_name: str
    description: str
    priority: TaskPriority
    start_date: str
    end_date: str
    days_to_start: int | None
    days_to_end: int | None


@dataclass(slots=True, frozen=True)
class FieldDefinition:
    """
    Definition of a single field in the topics form/table.

    Attributes
    ----------
    name : str
        Internal field name.
    caption : str
        Display label (table column header / form label).
    type : FieldType
        Field type (string, number, select, date).
    lines : int
        Number of lines (1 = Input, >1 = TextArea, -1 = auto-height TextArea).
    options : list | None
        Options for select fields.
    show_in_table : bool
        Whether to show this field as a table column.
    table_column_width : int
        Width of the table column (-1 = flexible / not shown).
    input_width : int | None
        Width of the input widget (None = full width).
    read_only : bool
        Whether the field is read-only.
    computed : str | None
        Computed value name ('created_date', 'edit_date', or None).
    """
    name: str
    caption: str
    type: FieldType
    lines: int
    options: list[str | int | float | bool] | None = None
    show_in_table: bool = True
    table_column_width: int = -1
    input_width: int | None = None
    read_only: bool = False
    computed: str | None = None
