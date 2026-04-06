from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key, Focus, Blur
from textual.widgets import Static, ListView, ListItem, Label
from rich.text import Text

from pylightlib.msc.Utils import Utils  # type: ignore

from tuido.domain.models import Task, TaskPriority
from tuido.services.tasks_service import TasksService


class CustomListView(ListView):
    """
    ListView that scrolls the parent VerticalScroll instead of itself.

    This is a workaround for a ListView scrolling issue in this layout.
    """

    vertical_scroll: VerticalScroll
    tasks_tab: TasksTab
    column_name: str
    loop_behavior: bool


    def __init__(
        self,
        vertical_scroll: VerticalScroll,
        tasks_tab: TasksTab,
        column_name: str,
        loop_behavior: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vertical_scroll = vertical_scroll
        self.vertical_scroll.can_focus = False
        self.tasks_tab = tasks_tab
        self.column_name = column_name
        self.loop_behavior = loop_behavior

    async def on_key(self, event: Key) -> None:
        loop_applied = self._enable_loop_behavior(event)
        self._scroll_to_selected_item(event, loop_applied)

    def _enable_loop_behavior(self, event: Key) -> bool:
        if not self.loop_behavior or event.key not in ('up', 'down'):
            return False
        current_index = self.index or 0
        list_bounds = (0, len(self.children) - 1)
        if current_index not in list_bounds:
            return False
        direction = -1 if event.key == 'up' else 1
        new_index = Utils.next_index(
            current_index,
            len(self.children),
            direction=direction,
            loop_behavior=self.loop_behavior,
        )
        self.index = new_index
        event.stop()
        return True

    def _scroll_to_selected_item(
        self, event: Key, loop_applied: bool
    ) -> None:
        index = self.index or 0
        if event.key not in ('up', 'down'):
            return
        if not loop_applied:
            if event.key == 'up':
                index = max(0, index - 1)
            elif event.key == 'down':
                index = min(len(self.children) - 1, index + 1)
        item = self.children[index]
        self.vertical_scroll.scroll_to_widget(item)
        self.change_class(index)
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = index

    def change_class(self, index: int) -> None:
        for i, item in enumerate(self.children):
            if isinstance(item, ListItem):
                if i == index:
                    item.add_class('selected')
                else:
                    item.remove_class('selected')

    def on_focus(self, event: Focus) -> None:
        for item in self.children:
            item.remove_class('selected')
        self.change_class(self.index or 0)
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = self.index or 0

    def on_blur(self, event: Blur) -> None:
        for item in self.children:
            item.remove_class('selected')

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        for item in self.children:
            item.remove_class('selected')
        event.item.add_class('selected')
        self.tasks_tab.selected_column_name = self.column_name
        self.tasks_tab.selected_task_index = self.index or 0


class TasksTab(Static):
    """
    Tasks tab — kanban-style board with one column per task state.

    Receives a TasksService and uses it to populate the columns on
    composition. All mutations (add/edit/delete/move) are triggered via
    TuidoApp action methods that call the service and then call
    ``refresh_column`` / ``select_task`` on this widget.
    """

    _service: TasksService
    list_views: dict[str, CustomListView]
    column_names: list[str]
    column_captions: dict[str, str]
    tasks: dict[str, list[Task]]
    selected_column_name: str
    selected_task_index: int


    def __init__(self, service: TasksService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._service = service
        self.list_views = {}
        self.column_names = service.get_column_names()
        self.column_captions = service.get_column_captions()
        self.tasks = service.get_tasks()
        # Default selection
        self.selected_column_name = self.column_names[0] if self.column_names else ''
        self.selected_task_index = 0

    def compose(self) -> ComposeResult:
        with Horizontal():
            for column_name in self.column_names:
                list_items = self.create_list_items(column_name)
                with Vertical():
                    yield Label(
                        Text(self.column_captions[column_name], style='bold'),
                        classes='task_column_header',
                    )
                    vscroll = VerticalScroll(classes='task_column_vscroll')
                    with vscroll:
                        list_view = CustomListView(
                            vscroll, self, column_name, True, *list_items
                        )
                        self.list_views[column_name] = list_view
                        yield list_view

    async def on_key(self, event: Key) -> None:
        if event.key == 'enter':
            self.app.action_tasks_edit()  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    #  List-item creation                                                  #
    # ------------------------------------------------------------------ #

    def create_list_items(self, column_name: str) -> list[ListItem]:
        list_items: list[ListItem] = []
        if column_name not in self.tasks:
            return list_items

        for task in self.tasks[column_name]:
            start_text, start_style = self._start_date_text_style(task)
            end_text, end_style     = self._end_date_text_style(task)

            list_item = ListItem(
                Static(Text(task.description, style='bold')),
                *([Static()] if start_text is not None or end_text is not None else []),
                *([Static(Text('▶ ' + start_text, style=start_style))]
                  if start_text is not None else []),
                *([Static(Text('◼ ' + end_text, style=end_style))]
                  if end_text is not None else []),
            )
            self._set_priority_class(list_item, task)
            list_items.append(list_item)

        return list_items

    def refresh_column(self, column_name: str) -> None:
        """Recreate the list view for the given column from service data."""
        self.tasks = self._service.get_tasks()
        list_view: ListView = self.list_views[column_name]
        list_view.clear()
        for item in self.create_list_items(column_name):
            list_view.append(item)
        self.set_can_focus()

    def select_task(self, column_name: str, index: int) -> None:
        """Focus the given column's list view and select the given index."""
        list_view = self.list_views[column_name]
        # Toggle focus to ensure on_focus fires
        list_view.can_focus = False
        list_view.disabled = True
        list_view.can_focus = True
        list_view.disabled = False
        list_view.index = index
        list_view.focus()
        list_view.refresh()

    def set_can_focus(self) -> None:
        """Enable/disable list view focus depending on whether it has items."""
        for col in self.column_names:
            has_items = col in self.tasks and len(self.tasks[col]) > 0
            self.list_views[col].can_focus = has_items

    # ------------------------------------------------------------------ #
    #  Date helpers                                                        #
    # ------------------------------------------------------------------ #

    def _start_date_text_style(
        self, task: Task
    ) -> tuple[str | None, str]:
        if not task.start_date:
            return None, ''
        text = f'{task.start_date} ({task.days_to_start} d)'
        d = task.days_to_start
        if d is None or d > 0:
            style = 'green'
        elif (task.end_date and d < 0
              and task.days_to_end is not None
              and task.days_to_end < 0):
            style = 'red'
        else:
            style = 'yellow'
        return text, style

    def _end_date_text_style(
        self, task: Task
    ) -> tuple[str | None, str]:
        if not task.end_date:
            return None, ''
        text = f'{task.end_date} ({task.days_to_end} d)'
        d = task.days_to_end
        if d is None or d > 0:
            style = 'green'
        elif d == 0:
            style = 'yellow'
        else:
            style = 'red'
        return text, style

    @staticmethod
    def _set_priority_class(item: ListItem, task: Task) -> None:
        match task.priority:
            case TaskPriority.HIGH:   item.add_class('task_prio_high')
            case TaskPriority.MEDIUM: item.add_class('task_prio_medium')
            case TaskPriority.LOW:    item.add_class('task_prio_low')
            case _:                   item.add_class('task_prio_none')
