import logging  # noqa # type: ignore
import re
from enum import Enum
from datetime import datetime, timedelta
from typing import Any

from textual import work
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, MaskedInput, ListView, Static, Footer

from pylightlib.textual.question_screen import QuestionScreen

from model.tasks_model import Task, TaskPriority
from model.config_model import Config


class DateName(Enum):
    """
    Enum for date field names.
    """
    START_DATE = 'start_date'
    END_DATE = 'end_date'


class DateAdjustment(Enum):
    """
    Enum for date adjustment types.
    """
    DECREASE = 'decrease'
    INCREASE = 'increase'


class TaskEditScreen(ModalScreen):
    """
    Popup for entering task details.

    This popup allows the user to enter a task description, select a priority,
    and specify start and end dates. It also includes a submit button to
    submit the entered data.

    Attributes
    ----------
    tuido_app : App
        The main application instance.
    list_views : dict[str, ListView | Any]
        Dictionary of list views for the tasks.
    description_input : Input
        Input field for task description.
    priority_input : Select
        Dropdown for selecting task priority.
    start_date_input : MaskedInput
        Input field for start date.
    start_date_weekday_label : Label
        Label for displaying the start date weekday.
    end_date_input : MaskedInput
        Input field for end date.
    end_date_weekday_label : Label
        Label for displaying the end date weekday.
    invalid_inputs : set[str]
        Set of IDs of invalid input fields.
    original_task : Task | None
        The original task object, if any, to be edited.
    """
    tuido_app: App
    list_views: dict[str, ListView | Any] = {}
    description_input: Input
    priority_input: Select
    start_date_input: MaskedInput
    start_date_weekday_label: Label
    end_date_input: MaskedInput
    end_date_weekday_label: Label
    invalid_inputs: set[str] = set()
    original_task: Task | None = None

    BINDINGS = [
        Binding(key='escape', key_display='ESC', action='close_modal',
                description='Cancel',
                tooltip='Discard changes and close the popup',
                show=True),
        Binding(key='enter', key_display='ENTER', action='save',
                description='Save',
                tooltip='Save changes and close the popup',
                priority=True,
                show=True),
        Binding(key='f1', key_display='F1',
                action='increase_start_date',
                description='Start+1',
                tooltip='Increase the start date by 1 day'),
        Binding(key='f2', key_display='F2',
                action='increase_end_date',
                description='End+1',
                tooltip='Increase the end date by 1 day'),
        Binding(key='f3', key_display='F3',
                action='decrease_start_date',
                description='Start-1',
                tooltip='Decrease the start date by 1 day'),
        Binding(key='f4', key_display='F4',
                action='decrease_end_date',
                description='End-1',
                tooltip='Decrease the end date by 1 day'),
        Binding(key='f9', key_display='F9',
                action='clear_start_date',
                description='Clear Start',
                tooltip='Clear the start date'),
        Binding(key='f10', key_display='F10',
                action='clear_end_date',
                description='Clear End',
                tooltip='Clear the end date'),
    ]


    class Submit(Message):
        """
        Message to be sent when the form is submitted.

        Attributes
        ----------
        description : str
            The task description.
        priority : Any
            The task priority.
        start_date : str
            The task start date.
        end_date : str
            The task end date.
        """
        def __init__(self, description: str, priority: Any, start_date: str,
                     end_date: str) -> None:
            self.description = description
            self.priority = priority
            self.start_date = start_date
            self.end_date = end_date
            super().__init__()


    def __init__(self, tuido_app: App, list_views: dict[str, ListView | Any],
                 **kwargs) -> None:
        """
        Initializes the popup with a dictionary of list views.

        Parameters
        ----------
        tuido_app : App
            The main application instance.
        list_views : dict[str, ListView | Any]
            A dictionary containing the list views for the tasks.
        **kwargs
            Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.tuido_app = tuido_app
        self.list_views = list_views

        self.description_input = Input(placeholder='Enter description')

        priorities = ['Low', 'Medium', 'High']
        self.priority_input = Select((option, option) for option in priorities)
        self.priority_input.id = 'priority_input'

        self.start_date_input = MaskedInput(
            id='start_date', template='9999-99-99;0', placeholder='YYYY-MM-DD'
        )

        self.start_date_weekday_label = Label(
            '', id='task_start_date_weekday_label'
        )

        self.end_date_input = MaskedInput(
            id='end_date', template='9999-99-99;0', placeholder='YYYY-MM-DD'
        )

        self.end_date_weekday_label = Label(
            '', id='task_end_date_weekday_label'
        )

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets for the popup.

        This includes input fields for task description, priority, start date,
        end date, and a submit button.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        with Static(id='main_container'):
            yield Label('Description:')
            yield self.description_input

            # Priority
            yield Label('Priority:')
            yield self.priority_input

            with HorizontalGroup():
                # Start Date
                with VerticalGroup():
                    yield Label('Start Date:')
                    yield HorizontalGroup(
                        self.start_date_input,
                        self.start_date_weekday_label
                    )

                # End Date
                with VerticalGroup():
                    yield Label('End Date:')
                    yield HorizontalGroup(
                        self.end_date_input,
                        self.end_date_weekday_label
                    )
            footer = Footer()
            footer.compact = True
            yield footer

    def check_action(self, action: str, parameters: tuple[object, ...]) \
    -> bool | None:
        """
        Checks if an action should be processed or ignored.

        Parameters
        ----------
        action : str
            The action name.
        parameters : tuple[object, ...]
            The action parameters.

        Returns
        -------
        bool | None
            True if the action should be processed, None if it should be ignored.
        """
        # Suppress the save action if the priority input has focus or is
        # expanded
        priority_input: Select = self.priority_input
        if action == 'save':
            if priority_input.has_focus or priority_input.expanded:
                return None

        # Otherwise, process the action normally
        return super().check_action(action, parameters)

    @work
    async def action_close_modal(self) -> None:
        """
        Closes the modal popup without saving changes.

        Asks the user to confirm if there are unsaved changes.
        """
        discard = await self.discard_unsaved_changes()

        if discard:
            self.app.pop_screen()

    def action_save(self) -> None:
        """
        Saves the changes made in the popup and closes it.
        """
        self.app.pop_screen()
        self.submit_changes()

    def action_decrease_start_date(self) -> None:
        """
        Decreases the start date by 1 day.
        """
        self.adjust_date(DateName.START_DATE, DateAdjustment.DECREASE)

    def action_increase_start_date(self) -> None:
        """
        Increases the start date by 1 day.
        """
        self.adjust_date(DateName.START_DATE, DateAdjustment.INCREASE)

    def action_decrease_end_date(self) -> None:
        """
        Decreases the end date by 1 day.
        """
        self.adjust_date(DateName.END_DATE, DateAdjustment.DECREASE)

    def action_increase_end_date(self) -> None:
        """
        Increases the end date by 1 day.
        """
        self.adjust_date(DateName.END_DATE, DateAdjustment.INCREASE)

    def action_clear_start_date(self) -> None:
        """
        Removes the value from the start date input field.
        """
        self.start_date_input.value = ''
        self.update_weekday_labels()
        self.start_date_input.refresh()

    def action_clear_end_date(self) -> None:
        """
        Removes the value from the end date input field.
        """
        self.end_date_input.value = ''
        self.update_weekday_labels()
        self.end_date_input.refresh()

    def synchronize_start_and_end_date(self, adjust_start_date: bool = False) \
    -> None:
        """
        Sets the end date to be the same as the start date if the start date is
        later than the end date.

        Parameters
        ----------
        adjust_start_date : bool, optional
            If True, adjusts the start date instead of the end date when the
            start date is after the end date (default is False).
        """
        # Parse the date values from the input fields
        try:
            start_date = datetime.strptime(
                self.start_date_input.value, "%Y-%m-%d"
            )
        except ValueError:
            start_date = None

        try:
            end_date = datetime.strptime(
                self.end_date_input.value, "%Y-%m-%d"
            )
        except ValueError:
            end_date = None

        if not start_date or not end_date:
            return

        # Adjust the end date if the start date is after the end date
        if start_date > end_date:
            if adjust_start_date:
                self.adjust_date(DateName.START_DATE, DateAdjustment.DECREASE)
            else:
                self.end_date_input.value = self.start_date_input.value

        self.update_weekday_labels()
        self.end_date_input.refresh()

    async def discard_unsaved_changes(self) -> bool:
        """
        Checks if there are unsaved changes in the popup.

        If there are unsaved changes, it prompts the user to confirm if they
        want to discard the changes.

        Returns
        -------
        bool
            True if the user confirms to discard changes, False otherwise.
        """
        # Parse the priority input value to compare with the original task
        tasks_model = self.tuido_app.tasks_controller.tasks_model
        priority_input_value = tasks_model.num_to_priority(tasks_model.priority_str_to_num(self.priority_input.value))

        # If there is no original task it means a new task is being created,
        # create a default original task object then to compare with user input
        if self.original_task:
            original_task = self.original_task
        else:
            original_task = Task(
                column_name='',
                description='',
                priority=TaskPriority.LOW,
                start_date='',
                end_date='',
                days_to_start=None,
                days_to_end=None
            )

        # Compare user input with the original task to check for changes
        if (
            self.description_input.value != original_task.description or
            priority_input_value != original_task.priority or
            self.start_date_input.value != original_task.start_date or
            self.end_date_input.value != original_task.end_date
        ):
            # There are unsaved changes, ask for confirmation
            if await self.tuido_app.push_screen_wait(
                QuestionScreen('Discard unsaved changes?'),
            ):
                return True
            else:
                return False
        return True

    def set_input_values(self, task: Task) -> None:
        """
        Sets the input values in the popup based on the provided task.

        Parameters
        ----------
        task : Task
            The task object containing the values to be set.
        """
        self.original_task = task
        self.description_input.value = task.description

        match task.priority:
            case TaskPriority.HIGH:
                task_priority = 'High'
            case TaskPriority.MEDIUM:
                task_priority = 'Medium'
            case TaskPriority.LOW:
                task_priority = 'Low'
            case TaskPriority.NONE:
                task_priority = None

        # self.priority_input.value = task_priority
        self.call_after_refresh(self._set_priority_value, task_priority)

        self.start_date_input.value = task.start_date
        self.end_date_input.value = task.end_date

    def _set_priority_value(self, priority: str | None) -> None:
        """
        Helper method to set the priority input value delayed.

        Parameters
        ----------
        priority : str | None
            The priority value to set.
        """
        if priority:
            self.priority_input.value = priority

    def adjust_date(self, date_name: DateName, adjustment: DateAdjustment) \
    -> None:
        """
        Adjusts the date in the input field based on the provided date name
        and adjustment type.

        Parameters
        ----------
        date_name : DateName
            The name of the date input field (start or end date).
        adjustment : DateAdjustment
            The type of adjustment (increase or decrease).
        """
        # Get the input widget instance and determine the adjustment factor
        match date_name:
            case DateName.START_DATE:
                input_widget: MaskedInput = self.start_date_input
            case _:
                input_widget: MaskedInput = self.end_date_input

        if adjustment == DateAdjustment.INCREASE:
            delta_factor = 1
        else:
            delta_factor = -1

        # Adjust the date in the input field
        if input_widget.value:
            # Try to parse the date and adjust it
            try:
                date = datetime.strptime(input_widget.value, "%Y-%m-%d")
                new_date = date + timedelta(days=1) * delta_factor
                input_widget.value = new_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        else:
            # If the input is empty, set it to today's date
            input_widget.value = datetime.now().strftime("%Y-%m-%d")

        # Make sure the start date is not after the end date
        if date_name == DateName.END_DATE \
        and adjustment == DateAdjustment.DECREASE:
            adjust_start_date = True
        else:
            adjust_start_date = False
        self.synchronize_start_and_end_date(adjust_start_date)
        input_widget.refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Handles input change events.

        Validates the input values for start and end dates. If the input is
        valid, it removes the invalid class from the input field. If the input
        is invalid, it adds the invalid class to the input field and stores the
        input ID in the invalid_inputs set.

        Also updates the weekday labels for the start and end date inputs.

        Parameters
        ----------
        event : Input.Changed
            The input change event.
        """
        if event.input.id in ['start_date', 'end_date']:
            value = event.value

            if self.is_valid_date(value) or value == '':
                if event.input.id in self.invalid_inputs:
                    self.invalid_inputs.remove(event.input.id)
                event.input.remove_class('invalid_input')
            else:
                self.invalid_inputs.add(event.input.id)
                event.input.add_class('invalid_input')

            self.update_weekday_labels()
            event.input.refresh()

    async def on_key(self, event: events.Key) -> None:
        """
        Handles key press events.

        If the Enter key is pressed, it triggers the save action.

        Parameters
        ----------
        event : events.Key
            The key press event.
        """
        pass
        # if event.key == 'enter':
        #     self.action_save()

        # if not self.priority_input.has_focus:
        #     if event.key == 'up':
        #         self.focus_previous()
        #     elif event.key == 'down':
        #         self.focus_next()

    def is_valid_date(self, date_str: str) -> bool:
        """
        Validates the date format.

        Checks if the date string is in the format YYYY-MM-DD and if it is a
        valid date.

        Parameters
        ----------
        date_str : str
            The date string to validate.

        Returns
        -------
        bool
            True if the date string is valid, False otherwise.
        """
        # Check if the date string matches the format YYYY-MM-DD
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            return False

        # Check if the date string is a valid date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def update_weekday_labels(self) -> None:
        """
        Sets the weekday labels for the start and end date inputs.

        This method updates the weekday labels based on the current values of
        the start and end date inputs.
        """
        self.start_date_weekday_label.update(
            self.get_weekday_name(self.start_date_input.value)
        )
        self.end_date_weekday_label.update(self.get_weekday_name(
            self.end_date_input.value)
        )

    def get_weekday_name(self, date_str: str) -> str:
        """
        Returns the name of the weekday for a given date string.

        Parameters
        ----------
        date_str : str
            The date string in the format YYYY-MM-DD.

        Returns
        -------
        str
            The name of the weekday, or empty string if invalid.
        """
        if not date_str:
            return ''

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            return f'({date.strftime("%A")})'
        except ValueError:
            return ''

    def submit_changes(self) -> None:
        """
        Submits the changes made in the popup.

        This method is called when the submit button is pressed. It sends a
        message with the entered data and clears the input fields.
        """
        if self.check_invalid_inputs():
            return
        else:
            self.post_message(self.Submit(
                self.description_input.value,
                self.priority_input.value,
                self.start_date_input.value,
                self.end_date_input.value
            ))

    def check_invalid_inputs(self) -> bool:
        """
        Checks if there are any invalid inputs.

        If there are invalid inputs, it shows an error message and returns
        True. Otherwise, it returns False.

        Returns
        -------
        bool
            True if there are invalid inputs, False otherwise.
        """
        if len(self.invalid_inputs) > 0:
            self.app.notify(
                'Please correct the invalid input(s) before submitting.',
                severity='error'
            )
            return True
        else:
            return False

    def set_list_view_state(self, enabled: bool) -> None:
        """
        Sets the state of the list views to either enabled or disabled.

        Parameters
        ----------
        enabled : bool
            If True, enables the list views; if False, disables them.
        """
        for list_view in self.list_views.values():
            list_view.can_focus = enabled
            list_view.disabled = not enabled

    async def on_unmount(self, event: Message):
        """
        Called when the popup is unmounted.

        This method is currently empty but can be used to perform any cleanup
        actions when the popup is removed from the screen.

        Parameters
        ----------
        event : Message
            The unmount event.
        """
        pass
