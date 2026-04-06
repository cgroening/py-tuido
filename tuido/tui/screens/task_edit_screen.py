import re
from enum import Enum
from datetime import datetime, timedelta
from typing import Any

from textual import work
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, MaskedInput, ListView, Static, Footer

from pylightlib.textual.question_screen import QuestionScreen  # type: ignore

from tuido.domain.models import Task, TaskPriority


class DateName(Enum):
    START_DATE = 'start_date'
    END_DATE   = 'end_date'


class DateAdjustment(Enum):
    DECREASE = 'decrease'
    INCREASE = 'increase'


class TaskEditScreen(ModalScreen):
    """
    Modal screen for creating or editing a task.

    Posts a ``Submit`` message when the user saves so that the parent
    (TuidoApp) can call the service and refresh the view.
    """

    BINDINGS = [
        Binding('escape', 'close_modal',          'Cancel',    show=True),
        Binding('enter',  'save',                 'Save',      priority=True, show=True),
        Binding('f1',     'increase_start_date',  'Start+1'),
        Binding('f2',     'increase_end_date',    'End+1'),
        Binding('f3',     'decrease_start_date',  'Start-1'),
        Binding('f4',     'decrease_end_date',    'End-1'),
        Binding('f9',     'clear_start_date',     'Clear Start'),
        Binding('f10',    'clear_end_date',       'Clear End'),
    ]

    list_views: dict[str, ListView | Any]
    description_input: Input
    priority_input: Select
    start_date_input: MaskedInput
    start_date_weekday_label: Label
    end_date_input: MaskedInput
    end_date_weekday_label: Label
    invalid_inputs: set[str]
    original_task: Task | None


    class Submit(Message):
        """Fired when the user saves the task."""

        def __init__(
            self,
            description: str,
            priority: Any,
            start_date: str,
            end_date: str,
        ) -> None:
            self.description = description
            self.priority    = priority
            self.start_date  = start_date
            self.end_date    = end_date
            super().__init__()


    def __init__(
        self,
        list_views: dict[str, ListView | Any],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.list_views    = list_views
        self.invalid_inputs = set()
        self.original_task  = None

        self.description_input = Input(placeholder='Enter description')

        self.priority_input = Select(
            ((opt, opt) for opt in ('Low', 'Medium', 'High')),
            id='priority_input',
        )

        self.start_date_input = MaskedInput(
            id='start_date', template='9999-99-99;0', placeholder='YYYY-MM-DD'
        )
        self.start_date_weekday_label = Label('', id='task_start_date_weekday_label')

        self.end_date_input = MaskedInput(
            id='end_date', template='9999-99-99;0', placeholder='YYYY-MM-DD'
        )
        self.end_date_weekday_label = Label('', id='task_end_date_weekday_label')

    def compose(self) -> ComposeResult:
        with Static(id='main_container'):
            yield Label('Description:')
            yield self.description_input
            yield Label('Priority:')
            yield self.priority_input
            with HorizontalGroup():
                with VerticalGroup():
                    yield Label('Start Date:')
                    yield HorizontalGroup(
                        self.start_date_input,
                        self.start_date_weekday_label,
                    )
                with VerticalGroup():
                    yield Label('End Date:')
                    yield HorizontalGroup(
                        self.end_date_input,
                        self.end_date_weekday_label,
                    )
            footer = Footer()
            footer.compact = True
            yield footer

    def check_action(
        self, action: str, parameters: tuple[object, ...]
    ) -> bool | None:
        if action == 'save':
            if self.priority_input.has_focus or self.priority_input.expanded:
                return None
        return super().check_action(action, parameters)

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    @work
    async def action_close_modal(self) -> None:
        if await self._discard_unsaved_changes():
            self.app.pop_screen()

    def action_save(self) -> None:
        self.app.pop_screen()
        self._submit_changes()

    def action_decrease_start_date(self) -> None:
        self.adjust_date(DateName.START_DATE, DateAdjustment.DECREASE)

    def action_increase_start_date(self) -> None:
        self.adjust_date(DateName.START_DATE, DateAdjustment.INCREASE)

    def action_decrease_end_date(self) -> None:
        self.adjust_date(DateName.END_DATE, DateAdjustment.DECREASE)

    def action_increase_end_date(self) -> None:
        self.adjust_date(DateName.END_DATE, DateAdjustment.INCREASE)

    def action_clear_start_date(self) -> None:
        self.start_date_input.value = ''
        self._update_weekday_labels()
        self.start_date_input.refresh()

    def action_clear_end_date(self) -> None:
        self.end_date_input.value = ''
        self._update_weekday_labels()
        self.end_date_input.refresh()

    # ------------------------------------------------------------------ #
    #  Public helpers (called by TuidoApp)                                #
    # ------------------------------------------------------------------ #

    def set_input_values(self, task: Task) -> None:
        """Pre-fill the form with values from an existing task."""
        self.original_task           = task
        self.description_input.value = task.description
        self.start_date_input.value  = task.start_date
        self.end_date_input.value    = task.end_date

        priority_str: str | None
        match task.priority:
            case TaskPriority.HIGH:   priority_str = 'High'
            case TaskPriority.MEDIUM: priority_str = 'Medium'
            case TaskPriority.LOW:    priority_str = 'Low'
            case _:                   priority_str = None

        self.call_after_refresh(self._set_priority_value, priority_str)

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in ('start_date', 'end_date'):
            value = event.value
            if self._is_valid_date(value) or value == '':
                self.invalid_inputs.discard(event.input.id)
                event.input.remove_class('invalid_input')
            else:
                self.invalid_inputs.add(event.input.id)
                event.input.add_class('invalid_input')
            self._update_weekday_labels()
            event.input.refresh()

    async def on_key(self, event: events.Key) -> None:
        pass

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _set_priority_value(self, priority: str | None) -> None:
        if priority:
            self.priority_input.value = priority

    def adjust_date(
        self, date_name: DateName, adjustment: DateAdjustment
    ) -> None:
        widget = (
            self.start_date_input
            if date_name == DateName.START_DATE
            else self.end_date_input
        )
        delta = timedelta(days=1 if adjustment == DateAdjustment.INCREASE else -1)

        if widget.value:
            try:
                date = datetime.strptime(widget.value, '%Y-%m-%d')
                widget.value = (date + delta).strftime('%Y-%m-%d')
            except ValueError:
                pass
        else:
            widget.value = datetime.now().strftime('%Y-%m-%d')

        adjust_start = (
            date_name == DateName.END_DATE
            and adjustment == DateAdjustment.DECREASE
        )
        self._sync_dates(adjust_start)
        widget.refresh()

    def _sync_dates(self, adjust_start: bool = False) -> None:
        try:
            start = datetime.strptime(self.start_date_input.value, '%Y-%m-%d')
        except ValueError:
            start = None
        try:
            end = datetime.strptime(self.end_date_input.value, '%Y-%m-%d')
        except ValueError:
            end = None

        if start and end and start > end:
            if adjust_start:
                self.adjust_date(DateName.START_DATE, DateAdjustment.DECREASE)
            else:
                self.end_date_input.value = self.start_date_input.value

        self._update_weekday_labels()
        self.end_date_input.refresh()

    async def _discard_unsaved_changes(self) -> bool:
        from tuido.tui.app import TuidoApp
        app: TuidoApp = self.app  # type: ignore[assignment]
        prio_num = app.tasks_service.priority_str_to_num(
            self.priority_input.value
        )
        prio = app.tasks_service.num_to_priority(prio_num)

        original = self.original_task or Task(
            column_name='', description='', priority=TaskPriority.LOW,
            start_date='', end_date='', days_to_start=None, days_to_end=None,
        )

        if (
            self.description_input.value != original.description
            or prio != original.priority
            or self.start_date_input.value != original.start_date
            or self.end_date_input.value != original.end_date
        ):
            return bool(
                await app.push_screen_wait(QuestionScreen('Discard unsaved changes?'))
            )
        return True

    def _submit_changes(self) -> None:
        if self.invalid_inputs:
            self.app.notify(
                'Please correct the invalid input(s) before submitting.',
                severity='error',
            )
            return
        self.post_message(self.Submit(
            self.description_input.value,
            self.priority_input.value,
            self.start_date_input.value,
            self.end_date_input.value,
        ))

    def _update_weekday_labels(self) -> None:
        self.start_date_weekday_label.update(
            self._weekday_name(self.start_date_input.value)
        )
        self.end_date_weekday_label.update(
            self._weekday_name(self.end_date_input.value)
        )

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str):
            return False
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    @staticmethod
    def _weekday_name(date_str: str) -> str:
        if not date_str:
            return ''
        try:
            return f'({datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")})'
        except ValueError:
            return ''

    def set_list_view_state(self, enabled: bool) -> None:
        for lv in self.list_views.values():
            lv.can_focus = enabled
            lv.disabled  = not enabled
