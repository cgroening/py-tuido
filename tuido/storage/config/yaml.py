import os
import yaml
from tuido.domain.errors import ConfigNotFoundError
from tuido.domain.models import FieldDefinition, FieldType
from tuido.storage.config.base import BaseConfigRepository


class YamlConfigRepository(BaseConfigRepository):
    """
    Loads configuration from a YAML file.

    Parses the field definitions and task column definitions on construction
    and exposes them via the BaseConfigRepository interface.
    """

    _fields: list[list[dict]]
    _columns: list[FieldDefinition]
    _columns_dict: dict[str, FieldDefinition]
    _task_column_names: list[str]
    _task_column_captions: dict[str, str]


    def __init__(self, yaml_path: str | None = None) -> None:
        self._fields = []
        self._columns = []
        self._columns_dict = {}
        self._task_column_names = []
        self._task_column_captions = {}
        if yaml_path is not None:
            self.set_path(yaml_path)

    def set_path(self, yaml_path: str) -> None:
        if not os.path.exists(yaml_path):
            raise ConfigNotFoundError(yaml_path)

        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        self._fields = config_data['fields']
        self._columns = []
        self._columns_dict = {}
        self._task_column_names = []
        self._task_column_captions = {}

        for row in config_data['fields']:
            for col in row:
                field = FieldDefinition(
                    name              = col['name'],
                    caption           = col['caption'],
                    type              = self._parse_field_type(col['type']),
                    lines             = col.get('lines', 1),
                    options           = col.get('options', []),
                    show_in_table     = self._parse_show_in_table(
                                            col.get('table_column_width')
                                        ),
                    table_column_width= self._parse_column_width(
                                            col.get('table_column_width')
                                        ),
                    input_width       = col.get('input_width', None),
                    read_only         = col.get('read_only', False),
                    computed          = col.get('computed', None),
                )
                self._columns.append(field)
                self._columns_dict[col['name']] = field

        for task_col in config_data['task_columns']:
            name    = task_col['name']
            caption = task_col['caption']
            self._task_column_names.append(name)
            self._task_column_captions[name] = caption

    # ------------------------------------------------------------------ #
    #  BaseConfigRepository interface                                      #
    # ------------------------------------------------------------------ #

    def get_fields(self) -> list[list[dict]]:
        return self._fields

    def get_columns(self) -> list[FieldDefinition]:
        return self._columns

    def get_columns_dict(self) -> dict[str, FieldDefinition]:
        return self._columns_dict

    def get_task_column_names(self) -> list[str]:
        return self._task_column_names

    def get_task_column_captions(self) -> dict[str, str]:
        return self._task_column_captions

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_field_type(type_str: str) -> FieldType:
        match type_str.upper():
            case 'STRING': return FieldType.STRING
            case 'NUMBER': return FieldType.NUMBER
            case 'SELECT': return FieldType.SELECT
            case 'DATE':   return FieldType.DATE
            case _: raise ValueError(f'Unknown field type: {type_str}')

    @staticmethod
    def _parse_show_in_table(width: str | None) -> bool:
        return width is not None and int(width) >= 0

    @staticmethod
    def _parse_column_width(width: str | None) -> int:
        if width is not None and int(width) >= 0:
            return int(width)
        return -1
