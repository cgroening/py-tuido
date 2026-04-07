import asyncio
import logging
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Input, Select, TextArea

from termz.tui.question_screen import QuestionScreen  # type: ignore
from termz.tui.theme_loader import ThemeLoader        # type: ignore

from tuido import APP_TITLE
from tuido.services.config_service import ConfigService
from tuido.services.notes_service import NotesService
from tuido.services.tasks_service import TasksService
from tuido.services.topics_service import TopicsService
from tuido.tui.bindings import CUSTOM_BINDINGS
from tuido.tui.screens.main_screen import MainScreen
from tuido.tui.screens.task_edit_screen import TaskEditScreen
from tuido.tui.screens.tabs.tasks_tab import TasksTab
from tuido.tui.screens.tabs.topics_tab import TopicsTab


_STATE_DIR       = Path.home() / '.local' / 'state' / 'tuido'
_STATE_DIR.mkdir(parents=True, exist_ok=True)
THEME_CONFIG_FILE = _STATE_DIR / 'theme.json'
THEMES_DIR        = str(Path(__file__).parent / 'themes')
DEFAULT_THEME     = 'classic-black'
theme_loader      = ThemeLoader(THEMES_DIR, include_standard_themes=True)


class TuidoApp(App):
    """
    Root Textual application for Tuido.

    Holds all four services and the single MainScreen reference.
    Owns all BINDINGS and action methods; delegates UI mutations to
    the tab widgets and service calls to the service layer.
    """

    TITLE    = APP_TITLE
    CSS_PATH = 'global.tcss'
    BINDINGS = CUSTOM_BINDINGS.get_bindings()  # type: ignore

    config_service: ConfigService
    tasks_service: TasksService
    topics_service: TopicsService
    notes_service: NotesService

    _main_screen: MainScreen
    _task_action: str  # 'new' | 'edit'
    _index_of_edited_task: int

    def __init__(
        self,
        config_service: ConfigService,
        tasks_service: TasksService,
        topics_service: TopicsService,
        notes_service: NotesService,
    ) -> None:
        super().__init__()
        self.config_service  = config_service
        self.tasks_service   = tasks_service
        self.topics_service  = topics_service
        self.notes_service   = notes_service
        self._task_action    = 'new'
        self._index_of_edited_task = -1

    def on_mount(self) -> None:
        """Register themes, set previous theme and push MainScreen."""
        theme_loader.register_themes_in_textual_app(self)
        theme_loader.set_previous_theme_in_textual_app(
            self, DEFAULT_THEME, THEME_CONFIG_FILE
        )
        self.update_header_theme_name()
        self._main_screen = MainScreen(
            self.config_service,
            self.tasks_service,
            self.topics_service,
            self.notes_service,
        )
        self.push_screen(self._main_screen)
        logging.info('TuidoApp mounted.')

    # ------------------------------------------------------------------ #
    #  Theme                                                               #
    # ------------------------------------------------------------------ #

    def watch_theme(self, theme_name: str) -> None:
        self.update_header_theme_name()
        theme_loader.save_theme_to_config(theme_name, THEME_CONFIG_FILE)
        theme_loader.load_theme_css(theme_name, self)

    def update_header_theme_name(self) -> None:
        self.title = f'{self.TITLE} - Theme: {self.theme}'

    # ------------------------------------------------------------------ #
    #  check_action — shows/hides bindings per active tab                 #
    # ------------------------------------------------------------------ #

    def check_action(
        self, action: str, parameters: tuple[object, ...]
    ) -> bool | None:
        try:
            active_group = self._main_screen.current_tab_name
        except Exception:
            active_group = 'tasks'
        return CUSTOM_BINDINGS.handle_check_action(
            action=action,
            _parameters=parameters,
            active_group=active_group,
        )

    # ------------------------------------------------------------------ #
    #  Global actions (themes + tab navigation)                           #
    # ------------------------------------------------------------------ #

    def action_next_theme(self) -> None:
        theme_loader.change_to_next_or_previous_theme(1, self)

    def action_prev_theme(self) -> None:
        theme_loader.change_to_next_or_previous_theme(-1, self)

    def action_toggle_dark(self) -> None:
        self.theme = (
            'textual-dark' if self.theme == 'textual-light' else 'textual-light'
        )

    def action_previous_tab(self) -> None:
        from textual.widgets import Tabs
        self._main_screen.query_one('#main_tabs', Tabs).action_previous_tab()

    def action_next_tab(self) -> None:
        from textual.widgets import Tabs
        self._main_screen.query_one('#main_tabs', Tabs).action_next_tab()

    # ------------------------------------------------------------------ #
    #  Tasks actions                                                       #
    # ------------------------------------------------------------------ #

    def action_tasks_new(self) -> None:
        self._open_task_edit_screen('new')

    def action_tasks_edit(self) -> None:
        self._open_task_edit_screen('edit')

    def action_tasks_move_left(self) -> None:
        self._move_task(-1)

    def action_tasks_move_right(self) -> None:
        self._move_task(1)

    def action_tasks_select_left_column(self) -> None:
        self._select_adjacent_column(-1)

    def action_tasks_select_right_column(self) -> None:
        self._select_adjacent_column(1)

    def action_tasks_select_upper_task(self) -> None:
        self._select_adjacent_task(-1)

    def action_tasks_select_lower_task(self) -> None:
        self._select_adjacent_task(1)

    @work
    async def action_tasks_delete(self) -> None:
        if await self.push_screen_wait(
            QuestionScreen('Really delete the selected task?')
        ):
            tasks_tab = self._get_tasks_tab()
            col   = tasks_tab.selected_column_name
            index = tasks_tab.selected_task_index
            self.tasks_service.delete_task(col, index)
            tasks_tab.refresh_column(col)
            new_len = len(self.tasks_service.get_tasks().get(col, []))
            asyncio.get_event_loop().call_soon(
                lambda: tasks_tab.select_task(
                    col, min(index, max(new_len - 1, 0))
                ) if new_len > 0 else None
            )
            self.notify('Task deleted!')
        else:
            self.notify('Deletion canceled.', severity='warning')

    def on_task_edit_screen_submit(
        self, message: TaskEditScreen.Submit
    ) -> None:
        """Handle task save from the edit screen."""
        logging.info(f'on_task_edit_screen_submit: {message}')
        tasks_tab = self._get_tasks_tab()
        task_raw = {
            'description': message.description,
            'priority':    str(
                self.tasks_service.priority_str_to_num(message.priority)
            ),
            'start_date':  message.start_date,
            'end_date':    message.end_date,
        }

        if self._task_action == 'new':
            col = self.config_service.get_task_column_names()[0]
            task, idx = self.tasks_service.add_task(col, task_raw)
        else:
            col   = tasks_tab.selected_column_name
            index = tasks_tab.selected_task_index
            task, idx = self.tasks_service.update_task(col, index, task_raw)

        tasks_tab.refresh_column(col)
        self._index_of_edited_task = idx

        asyncio.get_event_loop().call_soon(
            lambda: tasks_tab.select_task(col, idx)
        )
        self.call_later(lambda: tasks_tab.select_task(col, idx))

    # ------------------------------------------------------------------ #
    #  Topics actions                                                      #
    # ------------------------------------------------------------------ #

    def action_topics_new(self) -> None:
        topics_tab = self._get_topics_tab()
        if len(topics_tab.user_changed_inputs) > 0:
            self.notify('Discard or save changes first.', severity='warning')
            return
        topics_tab.create_new_topic()

    def action_topics_focus_table(self) -> None:
        table = self._main_screen.query_one('#topics_table', DataTable)
        self.set_focus(table)
        self.notify('Topics table focused!')

    def action_topics_save(self) -> None:
        topics_tab = self._get_topics_tab()
        topics_tab.save_topic()
        for field in list(topics_tab.user_changed_inputs):
            topics_tab.query_one(f'#{field}').remove_class('changed-input')
        topics_tab.topics_table.disabled = False
        topics_tab.user_changed_inputs.clear()
        self.notify('Topic updated!')

    @work
    async def action_topics_discard(self) -> None:
        if await self.push_screen_wait(QuestionScreen('Really discard changes?')):
            topics_tab = self._get_topics_tab()
            topics_tab.update_input_fields(called_from_discard=True)
            for field in list(topics_tab.user_changed_inputs):
                topics_tab.query_one(f'#{field}').remove_class('changed-input')
            topics_tab.topics_table.disabled = False
            topics_tab.user_changed_inputs.clear()
            self.notify('Changes discarded!')
        else:
            self.notify('Discard canceled.', severity='warning')

    @work
    async def action_topics_delete(self) -> None:
        if await self.push_screen_wait(
            QuestionScreen('Really delete the selected topic?')
        ):
            self._get_topics_tab().delete_topic()
            self.notify('Topic deleted!')
        else:
            self.notify('Deletion canceled.', severity='warning')

    # ------------------------------------------------------------------ #
    #  Notes actions                                                       #
    # ------------------------------------------------------------------ #

    def action_notes_show_textarea(self) -> None:
        notes_tab = self._main_screen.notes_tab
        notes_tab.query_one('#notes_textarea', TextArea).remove_class('hidden')
        notes_tab.query_one('#notes_markdown').add_class('hidden')

    def action_notes_show_md(self) -> None:
        notes_tab = self._main_screen.notes_tab
        notes_tab.query_one('#notes_textarea', TextArea).add_class('hidden')
        notes_tab.query_one('#notes_markdown').remove_class('hidden')

    def action_notes_show_textarea_and_md(self) -> None:
        notes_tab = self._main_screen.notes_tab
        notes_tab.query_one('#notes_textarea', TextArea).remove_class('hidden')
        notes_tab.query_one('#notes_markdown').remove_class('hidden')

    # ------------------------------------------------------------------ #
    #  Input-change tracking for topics (unchanged / changed highlighting) #
    # ------------------------------------------------------------------ #

    def on_input_changed(self, event: Input.Changed) -> None:
        input_name = event.input.id
        topics_tab = self._get_topics_tab()
        if input_name in topics_tab.programmatically_changed_inputs:
            topics_tab.programmatically_changed_inputs.discard(input_name)
            return
        self._compare_input_to_original(event)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        input_name = event.text_area.id
        topics_tab = self._get_topics_tab()
        if input_name in topics_tab.programmatically_changed_inputs:
            topics_tab.programmatically_changed_inputs.discard(input_name)
            return
        self._compare_input_to_original(event)

    def on_select_changed(self, event: Select.Changed) -> None:
        input_name = event.select.id
        topics_tab = self._get_topics_tab()
        if input_name in topics_tab.programmatically_changed_inputs:
            topics_tab.programmatically_changed_inputs.discard(input_name)
            return
        self._compare_input_to_original(event)

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        topics_tab = self._get_topics_tab()
        topics_tab.update_input_fields()
        topics_tab.app_startup = False

    def _compare_input_to_original(
        self, event: Input.Changed | TextArea.Changed | Select.Changed
    ) -> None:
        if isinstance(event, Input.Changed):
            widget      = event.input
            current_val = widget.value
        elif isinstance(event, TextArea.Changed):
            widget      = event.text_area
            current_val = widget.text
        elif isinstance(event, Select.Changed):
            widget      = event.select
            current_val = widget.value
        else:
            return

        if widget.id is None or not widget.id.startswith('topics_'):
            return

        if current_val == Select.BLANK:
            current_val = ''

        topics_tab = self._get_topics_tab()
        topic_id   = topics_tab.topics_table.get_current_id()
        field_name = widget.id.replace('topics_', '').replace('_input', '')

        row_data     = self.topics_service.get_topic_by_id(topic_id)
        original_val = str(row_data.get(field_name, ''))

        if current_val == original_val:
            widget.remove_class('changed-input')
            topics_tab.user_changed_inputs.discard(widget.id)
        else:
            widget.add_class('changed-input')
            topics_tab.user_changed_inputs.add(widget.id)

        self._update_topics_table_state()

    def _update_topics_table_state(self) -> None:
        topics_tab = self._get_topics_tab()
        topics_tab.topics_table.disabled = (
            len(topics_tab.user_changed_inputs) > 0
        )

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_tasks_tab(self) -> TasksTab:
        return self._main_screen.tasks_tab

    def _get_topics_tab(self) -> TopicsTab:
        return self._main_screen.topics_tab

    def _open_task_edit_screen(self, action: str) -> None:
        """Open the TaskEditScreen for 'new' or 'edit'."""
        self._task_action = action
        tasks_tab = self._get_tasks_tab()

        focused_col: str | None = None
        for col, lv in tasks_tab.list_views.items():
            if lv.has_focus:
                focused_col = col
                break

        if focused_col is None and action == 'edit':
            return

        screen = TaskEditScreen(tasks_tab.list_views)
        self.push_screen(screen)

        if action == 'edit':
            col   = tasks_tab.selected_column_name
            index = tasks_tab.selected_task_index
            task  = self.tasks_service.get_tasks()[col][index]
            screen.set_input_values(task)

    def _move_task(self, direction: int) -> None:
        """Move the selected task left (direction=-1) or right (+1)."""
        tasks_tab    = self._get_tasks_tab()
        col_names    = self.config_service.get_task_column_names()
        source_col   = tasks_tab.selected_column_name
        source_index = col_names.index(source_col)
        target_index = max(0, min(source_index + direction, len(col_names) - 1))

        if source_index == target_index:
            return
        if not self.tasks_service.get_tasks().get(source_col):
            return

        target_col = col_names[target_index]
        task_index = tasks_tab.selected_task_index
        task, new_idx = self.tasks_service.move_task(
            source_col, task_index, target_col
        )

        tasks_tab.refresh_column(source_col)
        tasks_tab.refresh_column(target_col)

        lv = tasks_tab.list_views[target_col]
        lv.index = new_idx
        lv.focus()

    def _select_adjacent_column(self, direction: int) -> None:
        """Move focus to the nearest non-empty column."""
        from termz.util.index import next_index  # type: ignore

        tasks_tab   = self._get_tasks_tab()
        list_views  = tasks_tab.list_views
        col_names   = self.config_service.get_task_column_names()

        if all(len(list_views[c].children) == 0 for c in col_names):
            return

        current_col   = tasks_tab.selected_column_name
        current_index = col_names.index(current_col)

        while True:
            current_index = Utils.next_index(
                current_index, len(col_names), direction
            )
            col = col_names[current_index]
            if len(list_views[col].children) > 0:
                list_views[col].focus()
                break

    def _select_adjacent_task(self, direction: int) -> None:
        """Select the task above (direction=-1) or below (+1)."""
        from termz.util.index import next_index  # type: ignore

        tasks_tab = self._get_tasks_tab()
        col       = tasks_tab.selected_column_name
        index     = tasks_tab.selected_task_index
        length    = len(self.tasks_service.get_tasks().get(col, []))

        if length == 0:
            return

        new_index = next_index(index, length, direction)
        self._index_of_edited_task = new_index
        tasks_tab.select_task(col, new_index)
