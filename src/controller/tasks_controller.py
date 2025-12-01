import asyncio
import enum
import logging

from textual.app import App
from textual.widgets import ListView

from pylightlib.msc.Utils import Utils

from model.config_model import Config  # type: ignore
from model.tasks_model import Task, Tasks    # type: ignore
from view.main_view import MainTabs  # type: ignore
from view.tasks_tab_edit_screen import TaskEditScreen  # type: ignore


class TaskAction(enum.Enum):
    NEW = 'new'
    EDIT = 'edit'


class TaskMoveDirection(enum.Enum):
    LEFT = -1
    RIGHT = 1


class TasksController:
    """
    Controller for managing tasks in the application.

    This class handles the interaction between the tasks model and the
    user interface. It provides methods for displaying the task form,
    saving tasks, moving tasks between columns, and deleting tasks.

    Attributes
    ----------
    config : Config
        The configuration object.
    tasks_model : Tasks
        The tasks model object.
    main_tabs : MainTabs
        The main tabs object.
    tuido_app : App
        The main application object.
    task_action : TaskAction
        The action to perform (new or edit).
    index_of_new_task : int
        The index of the most recently added or modified task (-1 if not applicable).
    """
    config: Config
    tasks_model: Tasks
    main_tabs: MainTabs
    tuido_app: App
    task_action: TaskAction
    index_of_new_task: int = -1


    def __init__(
        self, config: Config, tasks_model: Tasks, main_tabs: MainTabs,
        tuido_app: App
    ):
        """
        Initializes the TasksController.

        Parameters
        ----------
        config : Config
            The configuration object.
        tasks_model : Tasks
            The tasks model object.
        main_tabs : MainTabs
            The main tabs object.
        tuido_app : App
            The main application object.
        """
        self.config = config
        self.tasks_model = tasks_model
        self.main_tabs = main_tabs
        self.tuido_app = tuido_app

        # Set up the tasks tab with the tasks model data
        tasks_tab = self.main_tabs.tasks_tab
        tasks_tab.column_captions = self.tasks_model.column_captions
        tasks_tab.column_names = self.tasks_model.column_names
        tasks_tab.tasks = self.tasks_model.tasks

        logging.info(f'{tasks_model.tasks}')

    def show_task_form(self, task_action: TaskAction) -> None:
        """
        Displays the task form for creating or editing a task.

        Parameters
        ----------
        task_action : TaskAction
            The action to perform (new or edit).
        """
        self.task_action = task_action

        # Get the name of the focused list view, return if none is focused
        tasks_tab = self.main_tabs.tasks_tab
        focused_list_view_name: str | None = None

        for list_view_name, list_view in tasks_tab.list_views.items():
            if list_view.has_focus:
                focused_list_view_name = list_view_name
                break

        if focused_list_view_name is None and task_action == TaskAction.EDIT:
            return

        # Get the index of the selected task, return if none is selected
        if focused_list_view_name is None:
            selected_task_index = None
        if focused_list_view_name in tasks_tab.list_views:
            selected_task_index = tasks_tab.list_views[focused_list_view_name] \
                                      .index  # type: ignore
        if selected_task_index is None and task_action == TaskAction.EDIT:
            return

        # Show the screen creating or editing a task
        task_edit_screen = TaskEditScreen(
            self.tuido_app, self.main_tabs.tasks_tab.list_views
        )
        self.tuido_app.push_screen(task_edit_screen)
        self.set_task_form_input_values(task_edit_screen)

    def set_task_form_input_values(self, task_edit_screen: TaskEditScreen) \
    -> None:
        """
        Sets the input values for the task form based on the selected task
        if the task action is `TaskAction.EDIT`.

        Parameters
        ----------
        task_edit_screen : TaskEditScreen
            The task edit screen to set input values for.
        """
        if self.task_action == TaskAction.EDIT:
            # Get name of the active list view and index of the selected task
            tasks_tab = self.main_tabs.tasks_tab
            column_name = tasks_tab.selected_column_name
            selected_task_index = tasks_tab.selected_task_index

            # Get the selected task and set the input form values
            task = self.tasks_model.tasks[column_name][selected_task_index]
            # input_form = self.main_tabs.tasks_tab.input_form
            task_edit_screen.set_input_values(task)

    def save_task(self, message: TaskEditScreen.Submit) -> None:
        """
        Saves the task data from the input form to the tasks model
        and updates the view.

        This method is called when the user submits the task form.

        Parameters
        ----------
        message : TaskEditScreen.Submit
            The message containing the task data from the input form.
        """
        tasks_model = self.tasks_model

        # Get the task data from the input form
        task_raw = {
            'description': message.description,
            'priority':    tasks_model.priority_str_to_num(message.priority),
            'start_date':  message.start_date,
            'end_date':    message.end_date
        }

        # Determine the task action which was set when the form was opened
        if self.task_action == TaskAction.NEW:
            # New tasks will always go to the first column/inbox
            column_name = self.config.task_column_names[0]
        elif self.task_action == TaskAction.EDIT:
            column_name = self.main_tabs.tasks_tab.selected_column_name
            selected_task_index = self.main_tabs.tasks_tab.selected_task_index

            # Remove edited task from the current column
            tasks_model.delete_task(column_name, selected_task_index)

        # Add new or edited task to the tasks model and refresh the list view
        task = tasks_model.add_task_to_dict_from_raw_data(column_name, task_raw)
        tasks_model.save_to_file()
        self.recreate_list_view(column_name)
        self.store_index_of_new_task(column_name, task)

        # Delayed (re)selection of the new or edited task so UI is fully updated
        asyncio.get_event_loop().call_soon(
            lambda: self.reselect_list_view_item(column_name)
        )

        self.tuido_app.call_later(
            lambda: self.reselect_list_view_item(column_name)
        )

    def store_index_of_new_task(
        self, column_name: str, new_task: Task
    ) -> None:
        """
        Stores the index of the newly added or edited task.

        This is used to reselect the task in the list view after the edit
        screen is closed and the list view is recreated.

        Parameters
        ----------
        column_name : str
            The name of the column where the task was added or edited.
        new_task : Task
            The task that was added or edited.
        """
        tasks = self.tasks_model.tasks[column_name]

        for i, task in enumerate(tasks):
            if task == new_task:
                self.index_of_new_task = i
                return

        self.index_of_new_task = -1

    def recreate_list_view(self, column_name: str) -> None:
        """
        Recreates the list view for the specified column name.

        Parameters
        ----------
        column_name : str
            The name of the column to recreate the list view for.
        """
        # Remove all items
        tasks_tab = self.main_tabs.tasks_tab
        list_view: ListView = tasks_tab.list_views[column_name]
        list_view.clear()

        # Create a new instance of ListViewItem for each task in the column
        list_items = tasks_tab.create_list_items(column_name)
        for list_item in list_items:
            list_view.append(list_item)
        tasks_tab.set_can_focus()

    def reselect_list_view_item(self, list_view_name: str) -> None:
        """
        Re-selects the item in the list view that was selected before the popup
        was shown or the item that was just created.

        Parameters
        ----------
        list_view_name : str
            The name of the column to reselect the item in.
        """
        config: Config = Config.instance                    # type: ignore
        tasks_controller = self.tuido_app.tasks_controller  # type: ignore
        # tasks_tab = self.tuido_app.main_tabs.tasks_tab      # type: ignore
        tasks_tab = self.tuido_app.query_one('#tasks-tab')

        # list_view_name = tasks_tab.selected_column_name
        task_index = tasks_controller.index_of_new_task

        # Get the list view instance and set its state to enabled
        list_view = tasks_tab.list_views[list_view_name]

        # Set the selected index and focus the list view
        self.focus_listview(list_view, task_index)

    def focus_listview(self, list_view: ListView, selected_index: int) \
    -> None:
        """
        Focuses the specified list view and selects the specified index.

        Parameters
        ----------
        list_view : ListView
            The list view to be focused.
        selected_index : int
            The index of the item to be selected.
        """
        # Workaround to trigger the on_focus event of the list view
        # This is necessary to ensure the list view is focused correctly
        list_view.can_focus = False
        list_view.disabled = True
        list_view.can_focus = True
        list_view.disabled = False

        # Set the selected index and focus the list view
        list_view.index = selected_index
        list_view.focus()
        list_view.refresh()
        # list_view.refresh()

    def move_task(self, move_direction: TaskMoveDirection) -> None:
        """
        Moves the selected task to the left or right column.

        Parameters
        ----------
        move_direction : TaskMoveDirection
            The direction to move the task (left or right).
        """
        # Determine the index of the source column
        source_column_name = self.main_tabs.tasks_tab.selected_column_name
        column_names = self.config.task_column_names
        source_column_index = column_names.index(source_column_name)

        # Determine the index and name of the target column
        if move_direction == TaskMoveDirection.LEFT:
            target_column_index = \
                max(source_column_index - 1, 0)
        elif move_direction == TaskMoveDirection.RIGHT:
            target_column_index = \
                min(source_column_index + 1, len(column_names) - 1)

        target_column_name = self.config.task_column_names[target_column_index]

        # Abort conditions
        tasks_model = self.tasks_model
        if source_column_index == target_column_index:
            return

        if len(tasks_model.tasks[source_column_name]) == 0:
            return

        # Remove task from source column
        selected_task_index = self.main_tabs.tasks_tab.selected_task_index
        task_to_move = tasks_model.tasks[source_column_name] \
                           [selected_task_index]
        tasks_model.delete_task(source_column_name, selected_task_index)

        # Add task to target column
        task_to_move.column_name = target_column_name

        if target_column_name not in tasks_model.tasks:
            tasks_model.tasks[target_column_name] = []

        tasks_model.tasks[target_column_name].append(task_to_move)
        tasks_model.sort_tasks()
        tasks_model.save_to_file()

        # Update the source and target list views
        self.recreate_list_view(source_column_name)
        self.recreate_list_view(target_column_name)

        # Find the index of the moved task in the target column select it
        list_views: list[ListView] = self.main_tabs.tasks_tab.list_views
        target_list_view: ListView = list_views[target_column_name]

        target_task_index = 0
        for i, task in enumerate(self.tasks_model.tasks[target_column_name]):
            if task == task_to_move:
                target_task_index = i
                break

        target_list_view.index = target_task_index
        target_list_view.focus()

    def select_previous_or_next_column(
        self, direction: TaskMoveDirection
    ) -> None:
        """
        Selects the left or right column/list view in the tasks tab.

        Parameters
        ----------
        direction : TaskMoveDirection
            Which direction to focus to (left or right).
        """
        tasks_tab = self.main_tabs.tasks_tab
        list_views = tasks_tab.list_views

        # Abort if all columns/ListViews are empty
        if all(len(list_views[column_name].children) == 0
        for column_name in list_views):
            return

        # Get index of current column
        current_column_name = tasks_tab.selected_column_name
        column_names = self.config.task_column_names
        current_column_index = column_names.index(current_column_name)

        # Look for the next columns that has items
        while True:
            new_column_index = Utils.next_index(
                current_column_index, len(column_names), direction.value
            )
            new_column_name = column_names[new_column_index]
            list_view: ListView = list_views[new_column_name]
            current_column_index += direction.value

            # Stop a column with items is found
            if len(list_view.children) > 0:
                list_view.focus()
                break

    def delete_selected_task(self) -> None:
        """
        Deletes the selected task from the tasks model and updates the view.
        """
        tasks_tab = self.main_tabs.tasks_tab
        column_name = tasks_tab.selected_column_name
        selected_task_index = tasks_tab.selected_task_index

        # Delete the selected task if one is selected
        if selected_task_index is not None:
            self.tasks_model.delete_task(column_name, selected_task_index)
            self.tasks_model.save_to_file()
            self.recreate_list_view(column_name)

        # Selection of the tasks that jumps into the position of the deleted one
        asyncio.get_event_loop().call_soon(
            lambda: self._select_task(
                selected_task_index,
                len(self.tasks_model.tasks[column_name]),
                column_name
            )
        )

    def _select_task(
        self, task_index: int, list_length: int, column_name: str
    ) -> None:
        """
        Selects a task in the specified list view.

        Parameters
        ----------
        task_index : int
            The index of the task to select.
        list_length : int
            The length of the list to ensure the index is valid.
        column_name : str
            The name of the column/list view to select the task in.
        """
        if list_length > 0:
            new_index = min(task_index, list_length - 1)
            self.index_of_new_task = new_index
            self.reselect_list_view_item(column_name)
