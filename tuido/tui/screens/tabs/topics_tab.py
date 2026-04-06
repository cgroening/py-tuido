import logging

from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.widgets import Static, DataTable, Input, Label, Select, TextArea
from rich.text import Text

from pylightlib.textual.custom_data_table import CustomDataTable  # type: ignore

from tuido.domain.models import FieldDefinition, FieldType
from tuido.services.config_service import ConfigService
from tuido.services.topics_service import TopicsService


class TopicsDataTable(CustomDataTable):
    """DataTable for the topics list with row-cursor and ID helper."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = 'topics_table'
        self.cursor_type = 'row'

    def get_current_id(self) -> int:
        selected_row = self.get_row_at(self.cursor_row)
        return int(selected_row[0].plain.strip())


class TopicFormWidgets(VerticalGroup):
    """Form widgets auto-generated from the config field definitions."""

    _config: ConfigService


    def __init__(self, config: ConfigService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        for form_row in self._config.get_fields():
            with HorizontalGroup():
                for form_col in form_row:
                    yield self._create_form_element(form_col)

    def _create_form_element(
        self, form_col: dict
    ) -> VerticalGroup:
        label = Label(f'{form_col["caption"]}:')
        widget = self._create_widget(form_col)

        if form_col.get('read_only'):
            widget.disabled = True

        if form_col.get('input_width'):
            label.styles.width = form_col['input_width']
            widget.styles.width = form_col['input_width']

        group = VerticalGroup(label, widget)
        if form_col.get('input_width'):
            group.styles.width = form_col['input_width']
        return group

    def _create_widget(self, form_col: dict) -> Input | TextArea | Select:
        match form_col['type']:
            case 'string':
                if form_col.get('lines', 1) != 1:
                    return self._make_textarea(form_col)
                return self._make_input(form_col)
            case 'select':
                return self._make_select(form_col)
            case 'date':
                return self._make_input(form_col)
            case _:
                raise ValueError(f'Unsupported field type: {form_col["type"]}')

    @staticmethod
    def _make_input(form_col: dict) -> Input:
        return Input(id=f'topics_{form_col["name"]}_input', classes='form-input')

    @staticmethod
    def _make_textarea(form_col: dict) -> TextArea:
        ta = TextArea(id=f'topics_{form_col["name"]}_input', classes='form-input')
        lines = form_col.get('lines', 3)
        if lines < 0:
            ta.styles.height = 'auto'
        else:
            ta.styles.height = lines + 2
        return ta

    @staticmethod
    def _make_select(form_col: dict) -> Select:
        s = Select((opt, opt) for opt in form_col.get('options', []))
        s.id = f'topics_{form_col["name"]}_input'
        s.classes = 'form-input'
        return s


class TopicsTab(Static):
    """
    Topics tab — a sortable DataTable plus a detail form below.

    Receives ConfigService and TopicsService and exposes helpers that
    TuidoApp action methods call to manipulate the table and form.
    """

    _config: ConfigService
    _service: TopicsService
    topics_table: TopicsDataTable

    app_startup: bool = True
    programmatically_changed_inputs: set[str]
    user_changed_inputs: set[str]


    def __init__(
        self,
        config: ConfigService,
        service: TopicsService,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._service = service
        self.topics_table = TopicsDataTable()
        self.programmatically_changed_inputs = set()
        self.user_changed_inputs = set()

    def compose(self) -> ComposeResult:
        yield self.topics_table
        vscroll = VerticalScroll()
        vscroll.can_focus = False
        vscroll.id = 'form_widgets_container'
        with vscroll:
            yield TopicFormWidgets(self._config)

    # ------------------------------------------------------------------ #
    #  Table initialisation (called from MainScreen.on_mount)             #
    # ------------------------------------------------------------------ #

    def initialize_table(self) -> None:
        """Populate columns and rows in the topics table."""
        self._create_columns()
        self._add_rows()

    def _create_columns(self) -> None:
        self.topics_table.add_column('ID', key='id')
        for col in self._config.get_columns():
            if col.show_in_table:
                if col.table_column_width > 0:
                    self.topics_table.add_column(
                        col.caption, width=col.table_column_width
                    )
                else:
                    self.topics_table.flexible_columns.append(
                        self.topics_table.add_column(col.caption)
                    )

    def _add_rows(self) -> None:
        for row in self._service.get_all_topics():
            cells = [Text(str(row['id']), justify='right')]
            for col in self._config.get_columns():
                if col.show_in_table:
                    cells.append(row.get(col.name, Text()))  # type: ignore
            self.topics_table.add_row(*cells)
        self._sort_table()

    def _sort_table(self) -> None:
        self.topics_table.sort(
            'id',
            key=lambda v: int(str(v).strip() or 0),
            reverse=True,
        )

    # ------------------------------------------------------------------ #
    #  Actions called by TuidoApp                                         #
    # ------------------------------------------------------------------ #

    def create_new_topic(self) -> None:
        """Create a new topic in the service and update the table."""
        topic = self._service.create_topic()
        new_id = topic['id']
        new_row = [Text(str(new_id), justify='right')]
        for col in self._config.get_columns():
            if col.show_in_table:
                new_row.append('')
        self.topics_table.add_row(*new_row)
        self._sort_table()
        self.topics_table.select_first_row()

    def save_topic(self, input_query_func) -> None:
        """
        Read all input widgets and save the currently selected topic.

        Parameters
        ----------
        input_query_func : Callable
            A function that takes a CSS selector and returns the widget.
        """
        topic_id = self.topics_table.get_current_id()
        if topic_id is None:
            return

        updated_topic = dict(self._service.get_topic_by_id(topic_id))
        col_counter = 1

        for field in self._config.get_columns():
            widget_id = f'#topics_{field.name}_input'
            match field.type:
                case FieldType.STRING:
                    if field.lines == 1:
                        widget: Input = input_query_func(widget_id)
                        value = widget.value
                    else:
                        widget: TextArea = input_query_func(widget_id)
                        value = widget.text
                case FieldType.SELECT:
                    widget: Select = input_query_func(widget_id)
                    value = '' if widget.value == Select.BLANK else widget.value
                case _:
                    widget: Input = input_query_func(widget_id)
                    value = widget.value

            updated_topic[field.name] = value

            if field.show_in_table:
                self._update_table_cell(col_counter, value)
                col_counter += 1

        self._service.update_topic(topic_id, updated_topic)
        self.update_input_fields(input_query_func)
        logging.info(f'TopicsTab: saved topic id={topic_id}.')

    def update_input_fields(
        self, input_query_func, called_from_discard: bool = False
    ) -> None:
        """Fill form inputs from the currently selected topic."""
        topic_id = self.topics_table.get_current_id()
        try:
            row_data = self._service.get_topic_by_id(topic_id)
        except Exception as e:
            logging.error(f'TopicsTab: topic {topic_id} not found: {e}')
            return

        for col in self._config.get_columns():
            try:
                value = str(row_data.get(col.name, ''))
                if not self.app_startup and not called_from_discard:
                    self.programmatically_changed_inputs.add(
                        f'topics_{col.name}_input'
                    )
                self._set_input_value(col, value, input_query_func)
            except Exception as e:
                if not self.app_startup and not called_from_discard:
                    self.programmatically_changed_inputs.add(
                        f'topics_{col.name}_input'
                    )
                self._set_input_value(col, '', input_query_func)
                logging.warning(
                    f'TopicsTab: input update failed for id={topic_id}, '
                    f'field={col.name}: {e}'
                )

    def delete_topic(self) -> None:
        topic_id = self.topics_table.get_current_id()
        if topic_id is None:
            return
        self.topics_table.delete_selected_row()
        self._service.delete_topic(topic_id)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _set_input_value(
        self, field: FieldDefinition, value: str, query_func
    ) -> None:
        match field.type:
            case FieldType.STRING:
                if field.lines == 1:
                    w: Input = query_func(f'#topics_{field.name}_input')
                    w.value = value
                else:
                    w: TextArea = query_func(f'#topics_{field.name}_input')
                    w.text = value
            case FieldType.SELECT:
                w: Select = query_func(f'#topics_{field.name}_input')
                if value == '':
                    w.clear()
                else:
                    w.value = value
            case _:
                w: Input = query_func(f'#topics_{field.name}_input')
                w.value = value

    def _update_table_cell(self, col_index: int, value: str) -> None:
        from textual.coordinate import Coordinate
        row_index = self.topics_table.cursor_row
        self.topics_table.update_cell_at(
            Coordinate(row_index, col_index), value
        )
