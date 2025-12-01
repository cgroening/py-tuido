import enum
import logging
from typing import Callable

from textual.widgets import DataTable, Input, Select, TextArea
from textual.coordinate import Coordinate
from rich.text import Text  # type: ignore # noqa

from pylightlib.msc.Singleton import Singleton  # type: ignore
from pylightlib.msc.DateTime import DateTime  # type: ignore

from model.config_model import Config, FieldType, FieldDefinition  # type: ignore
from model.topics_model import Topic    # type: ignore
from view.main_view import MainTabs  # type: ignore


class TopicAction(enum.Enum):
    """
    Enum for topic actions.
    """
    NEW = 'new'
    EDIT = 'edit'


class TopicsController(metaclass=Singleton):
    """
    Controller for managing topics.

    This class handles the initialization of the topics table and
    updating input fields based on the selected row.

    Attributes
    ----------
    config : Config
        The configuration object containing the table columns.
    topics_model : Topic
        The Topic model containing the data.
    main_tabs : MainTabs
        The main tabs widget for the app.
    app_startup : bool
        A flag indicating if the app is starting up.
    programmatically_changed_inputs : set[str]
        A set of inputs that were recently changed programmatically. Inputs in
        this set will not be considered as user changes the next time
        `on_input_changed()` is triggered.
    user_changed_inputs : set[str]
        A set of inputs that were changed by the user. If this set is not empty,
        the topics table will be disabled to prevent unsaved changes in the input
        fields from being lost.
    """
    config: Config
    topics_model: Topic
    main_tabs: MainTabs
    app_startup: bool = True
    programmatically_changed_inputs: set[str] = set()
    user_changed_inputs: set[str] = set()


    def __init__(self, config: Config, model: Topic, main_tabs: MainTabs):
        """
        Initializes the TopicsController with a configuration and model.

        Parameters
        ----------
        config : Config
            The configuration object containing the table columns.
        model : Topic
            The Topic model containing the data.
        main_tabs : MainTabs
            The main tabs widget for the app.
        """
        self.config = config
        self.topics_model = model
        self.main_tabs = main_tabs

    def initialize_topics_table(self, table: DataTable) -> None:
        """
        Initializes the table columns and rows based on config and data.

        Parameters
        ----------
        table : DataTable
            The DataTable widget to be initialized.
        """
        self.create_table_columns(table)
        self.add_table_rows(table)

    def create_table_columns(self, table: DataTable) -> None:
        """
        Creates the columns in the topics table based on the configuration file.

        Parameters
        ----------
        table : DataTable
            The DataTable widget to add columns to.
        """
        # Add ID column
        table.add_column('ID', key='id')

        # Add user defined columns
        for col in self.config.columns:
            if col.show_in_table:
                if col.table_column_width > 0:
                    table.add_column(col.caption, width=col.table_column_width)
                else:
                    table.flexible_columns.append(table.add_column(col.caption))


    def add_table_rows(self, table: DataTable) -> None:
        """
        Adds rows to the topics table based on the data in the model.

        Parameters
        ----------
        table : DataTable
            The DataTable widget to add rows to.
        """
        # Add rows to the table
        for row in self.topics_model.data:
            display_columns = []

            # ID
            display_columns.append(Text(str(row['id']), justify='right'))

            # User defined columns
            for col in self.config.columns:
                if col.show_in_table:
                    if col.name in row:
                        display_columns.append(row[col.name])  # type: ignore
                    else:
                        display_columns.append(Text())
            table.add_row(*display_columns)

        self.sort_table_by_id(table)

    def sort_table_by_id(self, table: DataTable) -> None:
        """
        Sorts the table by ID in descending order.

        Parameters
        ----------
        table : DataTable
            The DataTable widget to be sorted.
        """
        # table.sort('id', key=lambda id: int(id.plain), reverse=True)
        # table.sort('id', key=lambda id: int(str(id)), reverse=True)
        table.sort('id', key=lambda id: int(str(id).strip() or 0), reverse=True)

    def update_input_fields(self, input_query_func: Callable, called_from_discard = False) \
    -> None:
        """
        Fills inputs based on the selected row.

        Parameters
        ----------
        input_query_func : Callable
            A function to query input widgets by ID.
        called_from_discard : bool, optional
            Whether this method is called from the discard action (default is False).
        """
        # Get ID of the currently selected topic
        selected_id = self.main_tabs.topics_tab.topics_table.get_current_id()

        # Update input widgets
        try:
            row_data = self.topics_model.topics_by_id[selected_id]

            for col in self.config.columns:
                try:
                    # Get field value, set to empty string if not found
                    if col.name in row_data.keys():
                        value = str(row_data[col.name])
                    else:
                        value = ''

                    if not self.app_startup and not called_from_discard:
                        self.programmatically_changed_inputs \
                            .add(f'topics_{col.name}_input')
                    self.set_input_field_value(col, value, input_query_func)

                except Exception as e:
                    if not self.app_startup and not called_from_discard:
                        self.programmatically_changed_inputs \
                            .add(f'topics_{col.name}_input')
                    self.set_input_field_value(col, '', input_query_func)

                    logging.warning(
                        f'Input update failed for ID {selected_id}, column '
                        + f'"{col.name}": {e}'
                    )
        except Exception as e:
            logging.error(f'Topic {selected_id} not found: {e}')

    def set_input_field_value(self, field: FieldDefinition, value: str,
                              input_query_func: Callable) -> None:
        """
        Sets the value of the input field based on its type.

        Parameters
        ----------
        field : FieldDefinition
            The field definition object.
        value : str
            The value to set in the input field.
        input_query_func : Callable
            A function to query input widgets by ID.
        """
        match field.type:
            case FieldType.STRING:
                if field.lines == 1:
                    input_widget: Input = input_query_func(
                        f"#topics_{field.name}_input"
                    )
                    input_widget.value = value
                else:
                    input_widget: TextArea = input_query_func(
                        f"#topics_{field.name}_input"
                    )
                    input_widget.text = value
            case FieldType.SELECT:
                input_widget: Select = input_query_func(
                    f'#topics_{field.name}_input'
                )

                if value == '':
                    input_widget.clear()
                else:
                    input_widget.value = value
            case _:
                input_widget: Input = input_query_func(
                    f'#topics_{field.name}_input'
                )
                input_widget.value = value

    def create_new_topic(self) -> None:
        """
        Creates a new topic and updates the table and the model.
        """
        # Get new ID (max ID from existing topics + 1)
        new_id = max([topic['id'] for topic in self.topics_model.data],
                     default=0) + 1

        # Generate new row
        table = self.main_tabs.topics_tab.topics_table
        new_row_table = [Text(str(new_id), justify='right')]

        for col in self.config.columns:
            if col.show_in_table:  # Only fields that are visible in the table
                new_row_table.append('')

        # Add new row to the table and sort by ID
        table.add_row(*new_row_table)
        self.sort_table_by_id(table)

        # Add row to model data
        new_topic = {'id': new_id}
        for col in self.config.columns:
            new_topic[col.name] = ''

        new_topic = self.apply_field_function(new_topic, TopicAction.NEW)
        self.topics_model.create_new_topic(new_topic)

        # Select the new row in the table and clear input fields
        table.select_first_row()
        # self.clear_input_fields()

        logging.info(f'New topic created with ID {new_id}.')

    def save_topic(self, input_query_func: Callable) -> None:
        """
        Saves a topic to the model and updates the table.

        Parameters
        ----------
        input_query_func : Callable
            A function to query input widgets by ID.
        """
        topic_id = self.main_tabs.topics_tab.topics_table.get_current_id()
        if topic_id is None:
            logging.warning('No topic selected to be saved.')
            return

        # Loop fields
        updated_topic = self.topics_model.topics_by_id[topic_id]
        col_counter = 1
        for field in self.config.columns:
            # Get the value from the input widget
            input_widget_id = f'#topics_{field.name}_input'
            match field.type:
                case FieldType.STRING:
                    if field.lines == 1:
                        input_widget: Input = input_query_func(input_widget_id)
                        value = input_widget.value
                    else:
                        input_widget: TextArea = input_query_func(
                            input_widget_id
                        )
                        value = input_widget.text
                case FieldType.SELECT:
                    input_widget: Select = input_query_func(input_widget_id)

                    if input_widget.value == Select.BLANK:
                        value = ''
                    else:
                        value = input_widget.value
                case _:
                    input_widget: Input = input_query_func(input_widget_id)
                    value = input_widget.value

            # Update the topic data
            updated_topic[field.name] = value

            # Update table
            if field.show_in_table:
                self.update_table_row(col_counter, field, value)
                col_counter += 1

        # Update the model with the new value
        updated_topic = self.apply_field_function(updated_topic,
                                                  TopicAction.EDIT)
        self.topics_model.update_topic(topic_id, updated_topic)

        # Update the view
        self.update_input_fields(input_query_func)

        logging.info(f'Topic with ID {topic_id} updated.')

    def apply_field_function(
        self,
        topic: dict[str, str | int | float | bool],
        topic_action: TopicAction
    ) -> dict[str, str | int | float | bool]:
        """
        Applies field functions (e.g. 'created_date' or 'edit_date')
        to the topic based on the action (new/edit).

        Parameters
        ----------
        topic : dict[str, str | int | float | bool]
            The topic data to be updated.
        topic_action : TopicAction
            The action to perform (new or edit).

        Returns
        -------
        dict[str, str | int | float | bool]
            The updated topic data.
        """
        field_names = list(topic.keys())
        field_names.remove('id')

        for field_name in field_names:
            field_def: FieldDefinition = self.config.columns_dict[field_name]

            today = DateTime.today_date(english_format=True)

            match field_def.computed:
                case 'created_date':
                    if topic_action == TopicAction.NEW:
                        topic[field_name] = today
                case 'edit_date':
                    topic[field_name] = today
                case _:
                    pass

        return topic

    def update_table_row(
        self, col_index: int, field: FieldDefinition, value: str
    ) -> None:
        """
        Updates a row of the table.

        Parameters
        ----------
        col_index : int
            The index of the column to be updated.
        field : FieldDefinition
            The field definition object.
        value : str
            The new value to set in the table cell.
        """
        if not field.show_in_table:
            return

        table = self.main_tabs.topics_tab.topics_table
        row_index = table.cursor_row
        table.update_cell_at(Coordinate(row_index, col_index), value)

    def delete_topic(self) -> None:
        """
        Deletes a topic from the table and the model.
        """
        topic_id = self.main_tabs.topics_tab.topics_table.get_current_id()
        if topic_id is None:
            logging.warning('No topic selected for deletion.')
            return

        # Delete selected row from table
        self.main_tabs.topics_tab.topics_table.delete_selected_row()

        # Delete topic from model
        self.topics_model.delete_topic(topic_id)

        logging.info(f'Topic with ID {topic_id} deleted.')
