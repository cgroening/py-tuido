from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Tabs, Tab

from view.topics_tab import TopicsTab
from view.tasks_tab import TasksTab
from view.notes_tab import NotesTab


class MainTabs(Container):
    """
    Main tabs container.

    Attributes
    ----------
    tuido_app : App
        The main application instance.
    current_tab_name : reactive
        The currently selected tab.
    tabs : Tabs
        The Tabs widget.
    topics_tab : TopicsTab
        The topics tab widget.
    tasks_tab : TasksTab
        The tasks tab widget.
    notes_tab : NotesTab
        The notes tab widget.
    """
    tuido_app: App
    current_tab_name = reactive('topics', bindings=True)
    tabs: Tabs
    topics_tab: TopicsTab
    tasks_tab: TasksTab
    notes_tab: NotesTab


    def __init__(self, tuido_app: App, **kwargs):
        """
        Initializes the MainTabs container.

        Parameters
        ----------
        tuido_app : App
            The main application instance.
        **kwargs
            Additional keyword arguments.
        """
        self.tasks_tab = TasksTab(tuido_app, id='tasks-tab')
        super().__init__(**kwargs)
        self.tuido_app = tuido_app
        self.topics_tab = TopicsTab(id='topics-tab', classes='hidden')
        self.notes_tab = NotesTab(id='notes-tab', classes='hidden')

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        # Tab labels
        self.tabs = Tabs(
            Tab('Tasks', id='tasks'),
            Tab('Topics', id='topics'),
            Tab('Notes', id='notes'),
            id='main_tabs',
        )
        self.tabs.can_focus = False
        yield self.tabs

        # Pre-create all tab contents, but only the current one will be visible
        yield self.tasks_tab
        yield self.topics_tab
        yield self.notes_tab

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """
        Handles tab change events.

        This method is called when a tab is activated. It hides all tabs except
        the selected one. It also updates the reactive variable `current_tab_name`
        to reflect the selected tab.

        Parameters
        ----------
        event : Tabs.TabActivated
            The event containing information about the activated tab.
        """
        if event.tab.id is not None:
            # Hide all tabs first
            for tab_id in ['topics', 'tasks', 'notes']:
                self.query_one(f'#{tab_id}-tab').add_class('hidden')

            # Show the selected tab and update reactive variable
            tab_to_show = f'#{event.tab.id}-tab'
            self.query_one(tab_to_show).remove_class('hidden')
            self.current_tab_name = event.tab.id
