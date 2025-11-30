import logging  # type: ignore # noqa

from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.widgets import Static, DataTable, Input, Label, Select, TextArea
from textual.widgets._data_table import ColumnKey, Column
from rich.text import Text  # type: ignore # noqa

from pylightlib.textual.custom_data_table import CustomDataTable

from model.config_model import Config, FieldDefinition  # type: ignore


# class TopicsDataTable(DataTable):
class TopicsDataTable(CustomDataTable):
    """
    DataTable for topics.

    Attributes:
        flexible_columns: List of column keys that should be flexible in width
            (will be adjusted according to window width).
    """
    # flexible_columns: list[ColumnKey] = []

    def __init__(self, **kwargs):
        """
        Initializes the DataTable for topics.
        """
        super().__init__(**kwargs)
        self.id = 'topics_table'
        self.cursor_type = 'row'

    # def on_resize(self) -> None:
    #     """
    #     Handles the resize event of the DataTable.

    #     Adjusts the widths of the flexible columns based on the new size of
    #     the table.
    #     """
    #     table_width = self.size.width - 10
    #     fixed_widths = self.get_fixed_column_widths()
    #     self.adjust_flexible_columns(table_width, fixed_widths)
    #     self.refresh()

    # def get_fixed_column_widths(self) -> int:
    #     """
    #     Returns the total width of all fixed-width columns in the table.

    #     This is used to calculate the available width for flexible columns.

    #     Returns:
    #         The total width of all fixed-width columns.
    #     """
    #     fixed_widths = 0

    #     for column_key in self.columns:
    #         column: Column = self.columns[column_key]

    #         if column_key not in self.flexible_columns:
    #             fixed_widths += column.width

    #     return fixed_widths

    # def adjust_flexible_columns(self, table_width: int, fixed_width: int) \
    # -> None:
    #     """
    #     Adjusts the widths of the flexible columns based on the available
    #     width in the table.

    #     Args:
    #         table_width: The total width of the table.
    #         fixed_width: The total width of all fixed-width columns.
    #     """
    #     for column_key in self.columns:
    #         column: Column = self.columns[column_key]

    #         if column_key in self.flexible_columns:
    #             column.auto_width = False
    #             column.width = int(
    #                 (table_width - fixed_width) / len(self.flexible_columns)
    #             )

    # def select_first_row(self) -> None:
    #     """
    #     Selects the first row in the table and posts a RowHighlighted event.
    #     """
    #     if self.row_count == 0:
    #         return

    #     # Set cursor to first row
    #     self.cursor_coordinate = (0, 0)
    #     self.move_cursor(row=0, column=0)  # Same as above, just to be sure

    #     # Manually post RowHighlighted event
    #     row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
    #     self.post_message(
    #         DataTable.RowHighlighted(self, self.cursor_row, row_key)
    #     )

    # def delete_selected_row(self) -> None:
    #     """
    #     Deletes the currently selected row from the table.
    #     """
    #     if self.cursor_row is not None:
    #         row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
    #         self.remove_row(row_key)

    def get_current_id(self) -> int:
        """
        Returns the ID of the currently selected topic.

        Returns:
            int: The ID of the currently selected topic.
        """
        selected_row = self.get_row_at(self.cursor_row)
        return int(selected_row[0].plain.strip())


class TopicFormWidgets(VerticalGroup):
    """
    Form widgets for the topics tab.
    """

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets.
        """
        for form_row in Config.instance.fields:
            with HorizontalGroup():
                for form_col in form_row:
                    yield self.create_form_element(form_col)


    def create_form_element(
        self, form_col: dict[str, str | int | float | bool ]
    ) -> VerticalGroup:
        """
        Creates a form element (label + input widget) based on the
        provided configuration.

        Args:
            form_col: A dictionary containing the field configuration.
                - 'name': The name of the field.
                - 'caption': The label for the field.
                - 'type': The type of the field (e.g., 'string', 'select').
                - 'options': The options for select fields.
                - 'input_width': The width of the input widget.
                - 'read_only': Whether the field is read-only.
        """
        # Create a label and input widget for each field
        label = Label(f'{form_col['caption']}:')
        form_widget = self.create_widget(form_col)

        # Read-only?
        if 'read_only' in form_col.keys() and form_col['read_only']:
            form_widget.disabled = True

        # Set width of label and input widget if specified
        if 'input_width' in form_col.keys() and form_col['input_width']:
                label.styles.width = form_col['input_width']
                form_widget.styles.width = form_col['input_width']

        # Group label and input
        vertical_group = VerticalGroup(label, form_widget)

        if 'input_width' in form_col.keys() and form_col['input_width']:
                vertical_group.styles.width = form_col['input_width']

        return vertical_group

    def create_widget(self, form_col: dict[str, str | int | float | bool]) \
        -> Input | TextArea | Select:
        """
        Creates a widget (Input, Select, ...) based on the field type.

        Args:
            form_col: A dictionary containing the field configuration.
        """
        form_widget: Input | TextArea | Select

        match form_col['type']:
            case 'string':
                # Input or TextArea?
                if 'lines' in form_col.keys() and int(form_col['lines']) != 1:
                    form_widget = self.create_textarea(form_col)
                else:
                    form_widget = self.create_input(form_col)
            case 'select':
                form_widget = self.create_select(form_col)
            case 'date':
                form_widget = self.create_input(form_col)
            case _:
                raise ValueError('Unsupported field type: ' +
                                    f'{form_col['type']}')

        return form_widget

    def create_input(self, form_col: dict[str, str | int | float | bool]) \
        -> Input:
        """
        Creates a new instance of Input (textbox) for the given field.

        Args:
            form_col: A dictionary containing the field configuration.
        """
        return Input(id=f'topics_{form_col['name']}_input',
                     classes='form-input')

    def create_textarea(
        self, form_col: dict[str, str | int | float | bool]
    ) -> TextArea:
        """
        Creates a new instance of Input (textbox) for the given field.

        Args:
            form_col: A dictionary containing the field configuration.
            height: Height of the TextArea (= number of lines).
        """
        textarea = TextArea(
            id=f'topics_{form_col['name']}_input', classes='form-input'
        )
        if form_col['lines'] < 0:
            textarea.styles.height = 'auto'
            # textarea.styles.height = form_col['lines'] + 2
        else:
            textarea.styles.height = form_col['lines'] + 2

        return textarea

    def create_select(self, form_col: dict[str, str | int | float | bool]) \
        -> Select:
        """
        Creates a new instance of Select (dropdown) for the given field.

        Args:
            form_col: A dictionary containing the field configuration.
        """
        select = Select((option, option) for option in form_col['options'])
        select.id = f'topics_{form_col['name']}_input'
        select.classes = 'form-input'

        return select

class TopicsTab(Static):
    """
    Topics tab content
    """
    topics_table: TopicsDataTable

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.topics_table = TopicsDataTable()

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets.
        """
        # Table with topics
        yield self.topics_table

        # Form widgets
        vscroll = VerticalScroll()
        vscroll.can_focus = False
        vscroll.id = 'form_widgets_container'
        with vscroll:
            yield TopicFormWidgets()
