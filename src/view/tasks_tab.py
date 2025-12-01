from __future__ import annotations
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key, Focus, Blur
from textual.widgets import Static, ListView, ListItem, Label
from rich.text import Text

from pylightlib.msc.Utils import Utils

from model.tasks_model import Task, TaskPriority


class CustomListView(ListView):
    """
    Custom ListView that scrolls the parent container (`VerticalScroll`).

    Normally, the ListView should be scrollable by itself, but it doesn't work
    as expected in this application. So this custom ListView that scrolls the
    parent container is used instead.

    This is a workaround until the ListView is fixed.

    Attributes
    ----------
    vertical_scroll : VerticalScroll
        The parent container that is scrolled.
    tasks_tab : TasksTab
        The TasksTab object that contains the list of tasks.
    column_name : str
        The name of the column the ListView belongs to.
    loop_behavior : bool
        Determines if the list view should loop when reaching the end.
    """
    vertical_scroll: VerticalScroll
    tasks_tab: TasksTab
    column_name: str
    loop_behavior: bool


    def __init__(self, vertical_scroll: VerticalScroll, tasks_tab: TasksTab,
                 column_name: str, loop_behavior: bool = True, *args, **kwargs):
        """
        Initializes the CustomListView.

        Parameters
        ----------
        vertical_scroll : VerticalScroll
            The parent container that is scrolled.
        tasks_tab : TasksTab
            The TasksTab object that contains the list of tasks.
        column_name : str
            The name of the column the ListView belongs to.
        loop_behavior : bool, optional
            Determines if the list view should loop when reaching the end
            (default is True).
        *args
            Positional arguments for the ListView.
        **kwargs
            Keyword arguments for the ListView.
        """
        super().__init__(*args, **kwargs)
        self.vertical_scroll = vertical_scroll
        self.vertical_scroll.can_focus = False
        self.tasks_tab = tasks_tab
        self.column_name = column_name
        self.loop_behavior = loop_behavior

    async def on_key(self, event: Key) -> None:
        """
        Handles key events for the ListView.

        Parameters
        ----------
        event : Key
            The key event that occurred.
        """
        loop_applied = self._enable_loop_behavior(event)
        self._scroll_to_selected_item(event, loop_applied)

    def _enable_loop_behavior(self, event: Key) -> bool:
        """
        Enables loop behavior for the ListView when the up or down key is
        pressed.

        If the loop behavior is enabled and the user presses the up key at
        the top of the list, the selection moves to the bottom of the list.
        If the user presses the down key at the bottom of the list, the
        selection moves to the top of the list.

        Parameters
        ----------
        event : Key
            The key event that occurred.

        Returns
        -------
        bool
            A boolean indicating whether loop behavior was applied.
        """
        # Abort if loop behavior is disabled or other key than up/down pressed
        if not self.loop_behavior or event.key not in ('up', 'down'):
            return False

        # Abort if current index is not the first or last index
        current_index = self.index or 0
        list_bounds = (0, len(self.children) - 1)
        if current_index not in list_bounds:
            return False

        # Determine the next index based on the key pressed
        direction = -1 if event.key == 'up' else 1
        new_index = Utils.next_index(
            current_index,
            len(self.children),
            direction=direction,
            loop_behavior=self.loop_behavior
        )

        # Update the index to the new index
        self.index = new_index

        # Disable further handling of this event, to ensure the correct handling
        # of scrolling and item selection in `_scroll_to_selected_item`
        event.stop()

        return True

    def _scroll_to_selected_item(self, event: Key, loop_applied: bool) -> None:
        """
        Scrolls the parent container to maintain the currently selected item
        in view if the up or down key was pressed.

        Furthermore, updates the class of the currently selected item and
        updates the selected item information in the TasksTab.

        Parameters
        ----------
        event : Key
            The key event that occurred.
        loop_applied : bool
            Indicates whether loop behavior was applied.
        """
        # Get index of the currently selected item
        index = self.index or 0

        # Abort if other key than up/down was pressed
        if event.key not in ('up', 'down'):
            return None

        # Adjust index if loop behavior was NOT applied (if loop_applied is
        # True, it means the index was already adjusted, so leave it as is)
        if not loop_applied:
            if event.key == 'up':
                index = max(0, index - 1)
            elif event.key == 'down':
                index = min(len(self.children) - 1, index + 1)

        # Get the item at the new index and scroll to it
        item = self.children[index]
        self.vertical_scroll.scroll_to_widget(item)
        self.change_class(index)
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = index or 0

    def change_class(self, index: int) -> None:
        """
        Changes the class of the currently selected item.

        This method is called to update the class of the currently selected item
        in the ListView. It removes the 'selected' class from all items and adds
        'selected' class to the currently selected item.

        Parameters
        ----------
        index : int
            The index of the currently selected item.
        """
        for i, item in enumerate(self.children):
            if isinstance(item, ListItem):
                if i == index:
                    item.add_class('selected')
                else:
                    item.remove_class('selected')

    def on_focus(self, event: Focus) -> None:
        """
        Handles the focus event for the ListView.

        This method is called when the ListView gains focus. It adds
        the 'selected' class to the currently selected item and removes it
        from all other items.

        Parameters
        ----------
        event : Focus
            The focus event.
        """
        for item in self.children:
            item.remove_class('selected')

        self.change_class(self.index or 0)
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = self.index or 0

    def on_blur(self, event: Blur) -> None:
        """
        Handles the blur event for the ListView.

        This method is called when the ListView loses focus. It removes the
        'selected' class from all items to indicate that no item is currently
        selected.

        Parameters
        ----------
        event : Blur
            The blur event.
        """
        for item in self.children:
            item.remove_class('selected')

    async def on_list_view_selected(self, event: ListView.Selected):
        """
        Handles the selection event for the ListView.

        This method is called when an item in the ListView is selected with
        the cursor. It adds the 'selected' class to the currently selected
        item and removes it from all other items.

        Parameters
        ----------
        event : ListView.Selected
            The selection event.

        Notes
        -----
        Function definition equivalent to:

        .. code-block:: python

            @on(ListView.Selected)
            def ...
        """
        for item in self.children:
            item.remove_class('selected')

        event.item.add_class('selected')
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = self.index or 0


class TasksTab(Static):
    """
    Tasks tab content.

    This class is used to display the tasks in a tabular format. Each column
    represents a different task category, and each row represents a task.

    The tasks are displayed in a list format, with the task description,
    start date, and end date shown. The tasks are color-coded based on their
    priority and the number of days until the start date and end date.

    The class uses the `CustomListView` to display the tasks in a scrollable
    list format. The `CustomListView` is a subclass of `ListView` that scrolls
    its parent container (`VerticalScroll`) instead of scrolling itself.

    Attributes
    ----------
    tuido_app : App
        The main application instance.
    list_views : dict[str, CustomListView]
        A dictionary of CustomListView objects for each column.
    column_names : list[str]
        A list of column names.
    column_captions : dict[str, str]
        A dictionary mapping column names to their captions.
    tasks : dict[str, list[Task]]
        A dictionary mapping column names to lists of Task objects.
    input_form : TasksInputPopup
        The input form for adding or editing tasks.
    selected_column_name : str
        The name of the currently selected column.
    selected_task_index : int
        The index of the currently selected task.
    """
    tuido_app: App
    list_views: dict[str, CustomListView] = {}
    column_names: list[str]
    column_captions: dict[str, str]
    tasks: dict[str, list[Task]]
    input_form: TasksInputPopup
    selected_column_name: str
    selected_task_index: int


    def __init__(self, tuido_app: App, **kwargs) -> None:
        """
        Initializes the TasksTab with the main application instance.

        Parameters
        ----------
        tuido_app : App
            The main application instance.
        **kwargs
            Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.tuido_app = tuido_app

    def compose(self) -> ComposeResult:
        """
        Composes the tasks tab content.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        with Horizontal():
            for column_name in self.column_names:
                list_items = self.create_list_items(column_name)

                with Vertical():
                    # Header for the column
                    text = Text(f'{self.column_captions[column_name]}',
                                style='bold')
                    yield(Label(text, classes='task_column_header'))

                    # ListView for the column
                    vscroll = VerticalScroll(classes='task_column_vscroll')
                    with vscroll:
                        list_view = CustomListView(
                            vscroll, self, column_name, True, *list_items
                        )
                        self.list_views[column_name] = list_view
                        yield list_view

    async def on_key(self, event: Key) -> None:
        """
        Handles key events for the ListView.

        Parameters
        ----------
        event : Key
            The key event that occurred.
        """
        if event.key == 'enter':
            self.tuido_app.action_tasks_edit()

    def create_list_items(self, column_name: str) -> list[ListItem]:
        """
        Creates a list of ListItem objects for the given column name.

        Each ListItem represents a task in the column.
        The ListItem contains the task description, start date, and end date.
        The start date and end date are color-coded based on the number of
        days until the date.

        Parameters
        ----------
        column_name : str
            The name of the column to create ListItems for.

        Returns
        -------
        list[ListItem]
            A list of ListItem objects representing the tasks in the column.
        """
        # Return empty list if the column doesn't have any tasks
        list_items: list[ListItem] = []
        if column_name not in self.tasks.keys():
            return list_items

        # Create a ListItem for each task
        for task in self.tasks[column_name]:
            start_date_text, start_date_style = \
                self.start_date_text_and_style(task)
            end_date_text, end_date_style = self.end_date_text_and_style(task)

            list_item = ListItem(
                # Description
                Static(Text(task.description, style='bold')),

                # Empty line if start date or end date is set
                *[Static()] if start_date_text is not None
                            or end_date_text is not None else [],

                # Start date
                *([Static(Text(
                    '▶ ' + start_date_text, style=start_date_style
                ))] if start_date_text is not None else []),

                # End date
                *([Static(Text(
                    '◼ ' + end_date_text, style=end_date_style
                ))] if end_date_text is not None else []),
            )

            self.set_priority_class(list_item, task)
            list_items.append(list_item)

        return list_items

    def start_date_text_and_style(self, task: Task) -> tuple[str | None, str]:
        """
        Returns the text and style for the start date of a task.

        The date text is formatted as "YYYY-MM-DD (x d)" where x is the
        number of days until the start date.

        The style is determined based on the number of days until the date:
            - Green: if the date is in the future (x > 0)
            - Yellow: if the date is today (x = 0)
            - Red: if the start date is in the past (x < 0) and end date is
                in the past, too.

        If the date is not set, it returns None for the text and an empty
        style string.

        Parameters
        ----------
        task : Task
            The task object.

        Returns
        -------
        tuple[str | None, str]
            A tuple containing the start date text and style.
        """
        start_date_text = None
        start_date_style = ''

        if task.start_date is not None and task.start_date != '':
            start_date_text = f'{task.start_date} ({task.days_to_start} d)'

            if task.days_to_start > 0:
                start_date_style = 'green'
            elif (task.end_date is not None and task.end_date != '') \
                 and (task.days_to_start < 0 and task.days_to_end < 0):
                start_date_style = 'red'
            elif task.days_to_start <= 0:
                start_date_style = 'yellow'

        return start_date_text, start_date_style

    def end_date_text_and_style(self, task: Task) -> tuple[str | None, str]:
        """
        Returns the text and style for the end date of a task.

        The date text is formatted as "YYYY-MM-DD (x d)" where x is the
        number of days until the end date.

        The style is determined based on the number of days until the date:
            - Green: if the date is in the future (x > 0)
            - Yellow: if the date is today (x = 0)
            - Red: if the date is in the past (x < 0)

        If the date is not set, it returns None for the text and an empty
        style string.

        Parameters
        ----------
        task : Task
            The task object.

        Returns
        -------
        tuple[str | None, str]
            A tuple containing the end date text and style.
        """
        end_date_text = None
        end_date_style = ''

        if task.end_date is not None and task.end_date != '':
            end_date_text = f'{task.end_date} ({task.days_to_end} d)'

            if task.days_to_end > 0:
                end_date_style = 'green'
            elif task.days_to_end == 0:
                end_date_style = 'yellow'
            elif task.days_to_end < 0:
                end_date_style = 'red'

        return end_date_text, end_date_style

    def set_priority_class(self, list_item: ListItem, task: Task) -> None:
        """
        Sets the class for the ListItem based on the task's priority.

        The class is used to color-code the task based on its priority:
            - High priority: 'task_prio_high'
            - Medium priority: 'task_prio_medium'
            - Low priority: 'task_prio_low'

        Parameters
        ----------
        list_item : ListItem
            The ListItem to set the class for.
        task : Task
            The task object.
        """
        match task.priority:
            case TaskPriority.HIGH:
                list_item.add_class('task_prio_high')
            case TaskPriority.MEDIUM:
                list_item.add_class('task_prio_medium')
            case TaskPriority.LOW:
                list_item.add_class('task_prio_low')
            case _:
                list_item.add_class('task_prio_none')

    def set_can_focus(self):
        """
        Checks if the ListView has any children and sets the can_focus
        attribute to True if it does.
        """
        for column_name in self.column_names:
            if column_name in self.tasks.keys() \
            and len(self.tasks[column_name]) > 0:
                self.list_views[column_name].can_focus = True
            else:
                self.list_views[column_name].can_focus = False
