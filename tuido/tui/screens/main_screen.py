from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Tabs, Tab
from termz.tui.custom_widgets.multiline_footer import MultiLineFooter  # type: ignore

from tuido import APP_ICON
from tuido.services.config_service import ConfigService
from tuido.services.notes_service import NotesService
from tuido.services.tasks_service import TasksService
from tuido.services.topics_service import TopicsService
from tuido.tui.bindings import CUSTOM_BINDINGS
from tuido.tui.screens.tabs.notes_tab import NotesTab
from tuido.tui.screens.tabs.tasks_tab import TasksTab
from tuido.tui.screens.tabs.topics_tab import TopicsTab


class MainScreen(Screen):
    """
    Primary screen containing the three main tabs (Tasks, Topics, Notes).

    Receives all services and passes them down to the appropriate tabs.
    Tab switching is handled manually (show/hide) to preserve the same
    behaviour as the original app and keep tab IDs ('tasks', 'topics',
    'notes') compatible with the bindings.yaml group names.
    """

    _config: ConfigService
    _tasks_service: TasksService
    _topics_service: TopicsService
    _notes_service: NotesService

    current_tab_name = reactive('tasks', bindings=True)

    tasks_tab: TasksTab
    topics_tab: TopicsTab
    notes_tab: NotesTab


    def __init__(
        self,
        config: ConfigService,
        tasks_service: TasksService,
        topics_service: TopicsService,
        notes_service: NotesService,
    ) -> None:
        super().__init__()
        self._config  = config
        self.tasks_tab  = TasksTab(tasks_service, id='tasks-tab')
        self.topics_tab = TopicsTab(config, topics_service, id='topics-tab',
                                    classes='hidden')
        self.notes_tab  = NotesTab(notes_service, id='notes-tab',
                                   classes='hidden')

    def compose(self) -> ComposeResult:
        yield Header(icon=APP_ICON)
        tabs = Tabs(
            Tab('Tasks',  id='tasks'),
            Tab('Topics', id='topics'),
            Tab('Notes',  id='notes'),
            id='main_tabs',
        )
        tabs.can_focus = False
        with Container():
            yield tabs
            yield self.tasks_tab
            yield self.topics_tab
            yield self.notes_tab
        yield MultiLineFooter(
            show_command_palette=True,
            compact=True,
            row_map=CUSTOM_BINDINGS.get_row_map(for_screen=True),
        )

    def on_mount(self) -> None:
        """Initialise the topics table after all widgets are mounted."""
        self.topics_tab.initialize_table()
        self.tasks_tab.set_can_focus()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Show the activated tab and hide the others."""
        if event.tab.id is None:
            return
        for tab_id in ('tasks', 'topics', 'notes'):
            self.query_one(f'#{tab_id}-tab').add_class('hidden')
        self.query_one(f'#{event.tab.id}-tab').remove_class('hidden')
        self.current_tab_name = event.tab.id
