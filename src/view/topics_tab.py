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

    Attributes
    ----------
    flexible_columns : list[ColumnKey]
        List of column keys that should be flexible in width
        (will be adjusted according to window width).
    """
    # flexible_columns: list[ColumnKey] = []

    def __init__(self, **kwargs):
        """
        Initializes the DataTable for topics.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments passed to the parent class.
        """
        super().__init__(**kwargs)
        self.id = 'topics_table'
        self.cursor_type = 'row'

    def get_current_id(self) -> int:
        """
        Returns the ID of the currently selected topic.

        Returns
        -------
        int
            The ID of the currently selected topic.
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

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        for form_row in Config.instance.fields:
            with HorizontalGroup():
                for form_col in form_row:
                    yield self.create_form_element(form_col)

    def create_form_element(
        self, form_col: dict[str, str | int | float | bool]
    ) -> VerticalGroup:
        """
        Creates a form element (label + input widget) based on the
        provided configuration.

        Parameters
        ----------
        form_col : dict[str, str | int | float | bool]
            A dictionary containing the field configuration.

            - 'name': The name of the field.
            - 'caption': The label for the field.
            - 'type': The type of the field (e.g., 'string', 'select').
            - 'options': The options for select fields.
            - 'input_width': The width of the input widget.
            - 'read_only': Whether the field is read-only.

        Returns
        -------
        VerticalGroup
            A vertical group containing the label and input widget.
        """
        # Create a label and input widget for each field
        label = Label(f'{form_col["caption"]}:')
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

        Parameters
        ----------
        form_col : dict[str, str | int | float | bool]
            A dictionary containing the field configuration.

        Returns
        -------
        Input | TextArea | Select
            The created widget based on the field type.

        Raises
        ------
        ValueError
            If the field type is unsupported.
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
                                 f'{form_col["type"]}')

        return form_widget

    def create_input(self, form_col: dict[str, str | int | float | bool]) \
        -> Input:
        """
        Creates a new instance of Input (textbox) for the given field.

        Parameters
        ----------
        form_col : dict[str, str | int | float | bool]
            A dictionary containing the field configuration.

        Returns
        -------
        Input
            A new Input widget instance.
        """
        return Input(id=f'topics_{form_col["name"]}_input',
                     classes='form-input')

    def create_textarea(
        self, form_col: dict[str, str | int | float | bool]
    ) -> TextArea:
        """
        Creates a new instance of TextArea for the given field.

        Parameters
        ----------
        form_col : dict[str, str | int | float | bool]
            A dictionary containing the field configuration.

        Returns
        -------
        TextArea
            A new TextArea widget instance.
        """
        textarea = TextArea(
            id=f'topics_{form_col["name"]}_input', classes='form-input'
        )
        if form_col['lines'] < 0:
            textarea.styles.height = 'auto'
        else:
            textarea.styles.height = form_col['lines'] + 2

        return textarea

    def create_select(self, form_col: dict[str, str | int | float | bool]) \
        -> Select:
        """
        Creates a new instance of Select (dropdown) for the given field.

        Parameters
        ----------
        form_col : dict[str, str | int | float | bool]
            A dictionary containing the field configuration.

        Returns
        -------
        Select
            A new Select widget instance.
        """
        select = Select((option, option) for option in form_col['options'])
        select.id = f'topics_{form_col["name"]}_input'
        select.classes = 'form-input'

        return select


class TopicsTab(Static):
    """
    Topics tab content.

    Attributes
    ----------
    topics_table : TopicsDataTable
        The data table widget for displaying topics.
    """
    topics_table: TopicsDataTable

    def __init__(self, **kwargs):
        """
        Initializes the TopicsTab.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments passed to the parent class.
        """
        super().__init__(**kwargs)
        self.topics_table = TopicsDataTable()

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        # Table with topics
        yield self.topics_table

        # Form widgets
        vscroll = VerticalScroll()
        vscroll.can_focus = False
        vscroll.id = 'form_widgets_container'
        with vscroll:
            yield TopicFormWidgets()
