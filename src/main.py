import logger  # noqa: F401  # Sets up logging, not used in code, !first import!
import logging
import argparse
from pathlib import Path

from textual import events, work
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Header, Tabs, DataTable, Input, Select, \
                            TextArea, Markdown

from pylightlib.textual import CustomBindings
from pylightlib.textual.question_screen import QuestionScreen

# from pylightlib.textual.custom_checkbox import CustomCheckbox
# from pylightlib.textual.custom_selection import CustomSelectionList
from pylightlib.textual.theme_loader import ThemeLoader

from model.config_model import Config
from model.notes_model import Notes
from model.tasks_model import Tasks
from model.topics_model import Topic
from view.main_view import MainTabs
from view.tasks_tab_edit_screen import TaskEditScreen
from controller.topics_controller import TopicsController
from controller.tasks_controller import TasksController, TaskAction, \
                                        TaskMoveDirection, TaskSelectDirection
from controller.notes_controller import NotesController


SCRIPT_DIR = Path(__file__).parent.parent
CUSTOM_BINDINGS = CustomBindings(
    yaml_file=f'{SCRIPT_DIR}/data/bindings.yaml',
    with_copy_paste_keys=True
)
THEME_CONFIG_FILE = Path.home() / '.textual_theme_lab_config.json'
DEFAULT_THEME = 'classic-black'
theme_loader = ThemeLoader(f'{SCRIPT_DIR}/themes', include_standard_themes=True)

class TuidoApp(App):
    """
    Main application class (main controller) for the Tuido app.

    Tuido app is a simple application that provides a user interface for
    managing topics, tasks and notes.

    Attributes
    ----------
    config : Config
        The configuration object for the app.
    topics_model : Topic
        The topics model.
    notes_model : Notes
        The notes model.
    topics_controller : TopicsController
        The controller object for managing topics.
    notes_controller : NotesController
        The controller object for managing notes.
    main_view : MainTabs
        Main view of the application, containing the main layout and widgets.
    popup_name : str | None
        The name of the currently displayed popup; None if no popup is shown.
    footer : Footer
        The footer widget of the app.
    last_escape_key : float
        Timestamp of the last 'escape' key press, used to toggle global key bindings.
    escape_pressed_twice : reactive
        Reactive flag indicating whether the 'escape' key was pressed twice.
    """
    TITLE = "Tuido"
    CSS_PATH = 'view/app_style.css'
    BINDINGS = CUSTOM_BINDINGS.get_bindings()  # type: ignore
    config: Config
    topics_model: Topic
    notes_model: Notes
    main_view: MainTabs
    topics_controller: TopicsController
    notes_controller: NotesController
    popup_name: str | None = None
    footer: Footer
    last_escape_key: float = 0.0
    escape_pressed_twice = reactive(False, bindings=True)


    def __init__(self) -> None:
        """
        Initializes the app.
        """
        super().__init__()

        # Get data folder from command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--data_folder', type=str)
        args = parser.parse_args()
        data_folder = args.data_folder if args.data_folder else 'data'

        # Config
        self.config = Config(f'{SCRIPT_DIR}/{data_folder}/config.yaml')

        # Theme Loader
        theme_loader.register_themes_in_textual_app(self)
        theme_loader.set_previous_theme_in_textual_app(
            self, DEFAULT_THEME, THEME_CONFIG_FILE
        )

        # Models
        self.tasks_model = Tasks(f'{SCRIPT_DIR}/{data_folder}/tasks.json')
        self.topics_model = Topic(f'{SCRIPT_DIR}/{data_folder}/topics.json')
        self.notes_model = Notes(f'{SCRIPT_DIR}/{data_folder}/notes.md')

        # Views
        self.main_view = MainTabs(self)

        # Controllers
        self.tasks_controller = TasksController(
            self.config, self.tasks_model, self.main_view, self
        )

        self.topics_controller = TopicsController(
            self.config, self.topics_model, self.main_view
        )

        self.notes_controller = NotesController(
            self.config, self.notes_model, self.main_view
        )

        logging.info('App initialized')

    def compose(self) -> ComposeResult:
        """
        Creates the child widgets.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        yield Header(icon='🗂️')
        yield self.main_view
        self.footer = Footer(show_command_palette=False)
        self.footer.compact = True
        yield self.footer

    def on_startup(self) -> None:
        """
        Gets called before mount.
        """
        pass

    def on_mount(self) -> None:
        """
        Initializes the app after mounting.
        """
        # self.screen.styles.debug = True
        self.update_header_theme_name()

        # Initialize the topics table
        table = self.query_one("#topics_table", expect_type=DataTable)
        self.topics_controller.initialize_topics_table(table)

        self.main_view.tasks_tab.set_can_focus()

    def on_ready(self) -> None:
        """
        Gets called after mounting.
        """
        # self.topics_controller.app_startup = False
        # self.main_view.tabs.active = self.main_view.current_tab_name
        pass

    async def on_key(self, event: events.Key) -> None:
        """
        Handles key press events.

        If the 'escape' key is pressed, it toggles the global key bindings
        based on the time interval between presses.

        Parameters
        ----------
        event : events.Key
            The key press event.
        """
        # self.notify(f'Key pressed: {event.key}')
        # if event.key == 'escape':
        #     if event.time - self.last_escape_key < 0.5:
        #         self.escape_pressed_twice = not self.escape_pressed_twice

        #     self.last_escape_key = event.time

        pass

    def watch_theme(self, theme_name: str) -> None:
        """
        Automatically called when `self.theme` changes.

        Writes the name of the theme to the config file and loads the CSS
        file(s) for the new theme.

        Parameters
        ----------
        theme_name : str
            The new theme name.
        """
        self.update_header_theme_name()
        theme_loader.save_theme_to_config(theme_name, THEME_CONFIG_FILE)
        theme_loader.load_theme_css(theme_name, self)

    def update_header_theme_name(self) -> None:
        """
        Updates the header to reflect the current theme name.
        """
        self.title = f'{self.TITLE} - Theme: {self.theme}'

    def check_action(self, action: str, parameters: tuple[object, ...]) \
    -> bool | None:
        """
        Checks if the action is valid for the current context.

        If the action is recognized, it will be handled by the
        `CUSTOM_BINDINGS` instance. The action is checked against the
        current active group (tab) and whether global keys should be shown
        based on the `escape_pressed_twice` flag.

        Parameters
        ----------
        action : str
            The action to check.
        parameters : tuple[object, ...]
            Parameters for the action.

        Returns
        -------
        bool | None
            True if the corresponding key of the action is to be displayed or
            None if not. False if the action is valid for the current context
            but is to be displayed as disabled.
        """
        return CUSTOM_BINDINGS.handle_check_action(
            action=action,
            parameters=parameters,
            active_group=str(self.main_view.current_tab_name),
            show_global_keys=bool(self.escape_pressed_twice)
        )

    async def action_global_copy_widget_value_to_clipboard(self) -> None:
        CUSTOM_BINDINGS.handle_copy_widget_value_to_clipboard(self)

    async def action_global_copy_selection_to_clipboard(self) -> None:
        CUSTOM_BINDINGS.handle_copy_selection_to_clipboard_action(self)

    async def action_global_paste_from_clipboard(self) -> None:
        CUSTOM_BINDINGS.handle_paste_from_clipboard(self)

    async def action_global_replace_widget_value_from_clipboard(self) -> None:
        CUSTOM_BINDINGS.handle_paste_from_clipboard(self, replace=True)

    def action_globalalways_next_theme(self) -> None:
        """
        Changes to the next theme in the list.
        """
        theme_loader.change_to_next_or_previous_theme(1, self)

    def action_globalalways_prev_theme(self) -> None:
        """
        Changes to the previous theme in the list.
        """
        theme_loader.change_to_next_or_previous_theme(-1, self)

    def action_globalalways_toggle_dark(self) -> None:
        """
        Toggles dark mode.
        """
        self.theme = (
            'textual-dark' if self.theme == 'textual-light' else 'textual-light'
        )

    def action_globalalways_previous_tab(self) -> None:
        """
        Selects the previous tab.
        """
        tabs = self.query_one('#main_tabs', expect_type=Tabs)
        tabs.action_previous_tab()

    def action_globalalways_next_tab(self) -> None:
        """
        Selects the next tab.
        """
        tabs = self.query_one('#main_tabs', expect_type=Tabs)
        tabs.action_next_tab()

    # Debugging
    # def action_app_get_focus(self) -> None:
    #     focused_widget = self.focused  # TODO: or self.screen.focused ?
    #     if focused_widget:
    #         # logging.info(f'Focus on: {focused_widget.id}')
    #         self.notify(f'Focus on: {focused_widget.id} ({type(focused_widget)})')
    #     else:
    #         # logging.info('No widget focused')
    #         self.notify('No widget focused')

    def action_shortcut_test(self) -> None:
        self.notify('The shortcut was triggered!')


    def action_tasks_new(self) -> None:
        """
        Displays the task form for creating a new task.
        """
        self.tasks_controller.show_task_form(TaskAction.NEW)

    def action_tasks_edit(self) -> None:
        """
        Displays the task form for editing the currently selected task.
        """
        self.tasks_controller.show_task_form(TaskAction.EDIT)

    def action_tasks_move_left(self) -> None:
        """
        Moves the currently selected task to the left column.
        """
        self.tasks_controller.move_task(TaskMoveDirection.LEFT)

    def action_tasks_move_right(self) -> None:
        """
        Moves the currently selected task to the right column.
        """
        self.tasks_controller.move_task(TaskMoveDirection.RIGHT)

    def action_tasks_select_left_column(self) -> None:
        """
        Moves the currently selected task to the right column.
        """
        self.tasks_controller.select_previous_or_next_column(TaskMoveDirection.LEFT)

    def action_tasks_select_right_column(self) -> None:
        """
        Moves the currently selected task to the right column.
        """
        self.tasks_controller.select_previous_or_next_column(TaskMoveDirection.RIGHT)

    def action_tasks_select_upper_task(self) -> None:
        """
        Selects the task above the currently selected one.
        """
        self.tasks_controller.select_upper_lower_task(TaskSelectDirection.UP)

    def action_tasks_select_lower_task(self) -> None:
        """
        Selects the task below the currently selected one.
        """
        self.tasks_controller.select_upper_lower_task(TaskSelectDirection.DOWN)

    @work
    async def action_tasks_delete(self) -> None:
        """
        Deletes the currently selected task.

        The user will be asked for confirmation before the task is deleted.
        """
        if await self.push_screen_wait(
            QuestionScreen('Really delete the selected task?'),
        ):
            self.tasks_controller.delete_selected_task()
            self.notify('Task deleted!')
        else:
            self.notify('Deletion canceled.', severity='warning')

    def action_topics_new(self) -> None:
        """
        Creates a new topic.
        """
        if len(self.topics_controller.user_changed_inputs) > 0:
            self.notify('Discard or save changes first.',
                        severity='warning')
            return

        self.topics_controller.create_new_topic()

    def action_topics_focus_table(self) -> None:
        """
        Focuses the topics table.
        """
        table = self.query_one('#topics_table', expect_type=DataTable)
        self.set_focus(table)
        self.notify('Topics table focused!')

    def action_topics_save(self) -> None:
        """
        Saves the currently selected topic.
        """
        # Update topics model with the values from the input fields
        self.topics_controller.save_topic(lambda id: self.query_one(id))

        # self.topics_controller.update_input_fields(
        #     lambda id: self.query_one(id), called_from_discard=True
        # )

        # Remove class "changed-input" from all changed inputs
        for field in self.topics_controller.user_changed_inputs:
            self.query_one(f'#{field}').remove_class('changed-input')

        # Re-enable the topics table which was disabled when the user changed an
        # input to prevent switching topics while there are unsaved changes
        self.main_view.topics_tab.topics_table.disabled = False
        self.topics_controller.user_changed_inputs.clear()
        self.notify('Topic updated!')

    @work
    async def action_topics_discard(self) -> None:
        """
        Discards the changes made to the currently selected topic.

        The input fields will be reset to the original values from the model.
        The topics table will be re-enabled. The user will be asked for
        confirmation before the changes are discarded.
        """
        if await self.push_screen_wait(
            QuestionScreen('Really discard changes?'),
        ):
            self.topics_controller.update_input_fields(
                lambda id: self.query_one(id), called_from_discard=True
            )
            self.notify('Changes discarded!')
        else:
            self.notify('Discard canceled.', severity='warning')

    @work
    async def action_topics_delete(self) -> None:
        """
        Deletes the currently selected topic.

        The user will be asked for confirmation before the topic is
        deleted.
        """
        if await self.push_screen_wait(
            QuestionScreen("Really delete the selected topic?"),
        ):
            self.topics_controller.delete_topic()
            self.notify('Topic deleted!')
        else:
            self.notify('Deletion canceled.', severity='warning')

    def action_notes_show_textarea(self) -> None:
        """
        Shows the textarea and hides the markdown.
        """
        textarea = self.query_one('#notes_textarea', expect_type=TextArea)
        markdown = self.query_one('#notes_markdown', expect_type=Markdown)
        textarea.remove_class('hidden')
        markdown.add_class('hidden')

    def action_notes_show_md(self) -> None:
        """
        Hides the textarea and shows the markdown.
        """
        textarea = self.query_one('#notes_textarea', expect_type=TextArea)
        markdown = self.query_one('#notes_markdown', expect_type=Markdown)
        textarea.add_class('hidden')
        markdown.remove_class('hidden')

    def action_notes_show_textarea_and_md(self) -> None:
        """
        Shows the textarea and markdown.
        """
        textarea = self.query_one('#notes_textarea', expect_type=TextArea)
        markdown = self.query_one('#notes_markdown', expect_type=Markdown)
        textarea.remove_class('hidden')
        markdown.remove_class('hidden')



    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        """
        Is triggered when a row in the DataTable is highlighted.

        This method updates the input fields with the values from the
        selected row.

        Parameters
        ----------
        event : DataTable.RowHighlighted
            The event containing information about the highlighted row.
        """
        self.topics_controller.update_input_fields(
            lambda id: self.query_one(id)
        )

        # Disable startup state after first selection
        # This is necessary to prevent the input fields from being
        # marked as changed when the app starts
        # and the topics table is initialized
        self.topics_controller.app_startup = False

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Is triggered when the value of an Input is changed.

        If the input field is changed programmatically, it will be ignored.
        Otherwise, `self.compare_input_value_to_original` is called.

        Parameters
        ----------
        event : Input.Changed
            The event containing information about the changed input.
        """
        input_name = event.input.id
        if input_name in self.topics_controller.programmatically_changed_inputs:
            self.topics_controller.programmatically_changed_inputs \
                .remove(input_name)
            return

        self.compare_input_value_to_original(event)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """
        Is triggered when the value of a TextArea is changed.

        If the input field is changed programmatically, it will be ignored.
        Otherwise, `self.compare_input_value_to_original` is called.

        Parameters
        ----------
        event : TextArea.Changed
            The event containing information about the changed input.
        """
        input_name = event.text_area.id

        # logging.info(f'input_name: {input_name}')

        # # TODO: Prüfen, ob topics_.... oder notes....

        if input_name in self.topics_controller.programmatically_changed_inputs:
            self.topics_controller.programmatically_changed_inputs.remove(
                input_name
            )
            return

        self.compare_input_value_to_original(event)

    # def on_tasks_input_popup_submit(self, message: TasksInputPopup.Submit) \
    # -> None:
    #     self.tasks_controller.save_task(message)

    def on_task_edit_screen_submit(self, message: TaskEditScreen.Submit) \
    -> None:
        logging.info(f'on_tasks_tab_edit_screen_submit: {message}')
        self.tasks_controller.save_task(message)

    def on_select_changed(self, event: Select.Changed) -> None:
        """
        Is triggered when the value of a Select is changed.

        If the input field is changed programmatically, it will be ignored.
        Otherwise, `self.compare_input_value_to_original` is called.

        Parameters
        ----------
        event : Select.Changed
            The event containing information about the changed select.
        """
        input_name = event.select.id
        if input_name in self.topics_controller.programmatically_changed_inputs:
            self.topics_controller.programmatically_changed_inputs \
                .remove(input_name)
            return

        self.compare_input_value_to_original(event)

    def compare_input_value_to_original(
        self, event: Input.Changed | TextArea.Changed | Select.Changed
    ) -> None:
        """
        Compares the current value of the input field to the original value
        from the model.

        If the values are different, the input field is marked as changed
        and the topics table is deactivated. If the values are the same,
        the input field is marked as unchanged and the topics table is
        activated.

        Parameters
        ----------
        event : Input.Changed | TextArea.Changed | Select.Changed
            The event containing information about the changed input.
        """
        # TODO: Cleanup/extract code to separate methods

        input_widget: Input | TextArea | Select

        # Get the input widget that triggered the event and the value of it
        if isinstance(event, Input.Changed):
            input_widget = event.input
            current_value = input_widget.value
        elif isinstance(event, TextArea.Changed):
            input_widget = event.text_area
            current_value = input_widget.text
        elif isinstance(event, Select.Changed):
            input_widget = event.select
            current_value = input_widget.value
        else:
            return

        # Ignore events from tabs other than "Topics"
        if input_widget.id is None or not input_widget.id.startswith('topics_'):
            return

        if current_value == Select.BLANK:
            current_value = ''

        # Get original value from the model
        topics_ctrl = self.topics_controller
        topic_id = self.main_view.topics_tab.topics_table.get_current_id()
        field_name = input_widget.id.replace('topics_', '') \
                                    .replace('_input', '')

        if field_name in topics_ctrl.topics_model.topics_by_id[topic_id].keys():
            original_value = topics_ctrl.topics_model \
                             .topics_by_id[topic_id][field_name]
        else:
            original_value = ''

        # Debugging
        # logging.info(
        #     f'compare_input_value_to_original: {input_widget.id} ' +
        #     f'current_value: {current_value}, ' +
        #     f'original_value: {original_value}')

        # Compare current value to original value

        if current_value == original_value:
            input_widget.remove_class('changed-input')

            if input_widget.id in topics_ctrl.user_changed_inputs:
                topics_ctrl.user_changed_inputs.remove(input_widget.id)
        else:
            input_widget.add_class('changed-input')
            topics_ctrl.user_changed_inputs.add(input_widget.id)

        # Change the state of the topics table
        self.activate_deactivate_topics_table()

    def activate_deactivate_topics_table(self) -> None:
        """
        Activates or deactivates the topics table based on the number of
        user changed inputs.

        If there are any user changed inputs, the topics table is
        deactivated (disabled). Otherwise, it is activated (enabled).
        This is used to prevent the user from selecting a different topic
        while there are unsaved changes in the current topic.
        """
        if len(self.topics_controller.user_changed_inputs) > 0:
            self.main_view.topics_tab.topics_table.disabled = True
        else:
            self.main_view.topics_tab.topics_table.disabled = False


    def _paste_into_input(self, input: Input, text: str) \
    -> None:
        """
        Pastes the given text into the input widget at the cursor position.

        Parameters
        ----------
        input : Input
            The input widget to paste into.
        text : str
            The text to paste.
        """
        cursor_pos = input.cursor_position or len(input.value)
        input.insert(text, cursor_pos)
        input.cursor_position = cursor_pos + len(text)
        self.notify('Text pasted into input field!')

    def _paste_into_textarea(self, textarea: TextArea, text: str) \
    -> None:
        """
        Pastes the given text into the textarea at the cursor position.

        Parameters
        ----------
        textarea : TextArea
            The textarea widget to paste into.
        text : str
            The text to paste.
        """
        cursor_pos: tuple[int, int] = textarea.cursor_location or (0, 0)
        textarea.insert(text, cursor_pos)
        textarea.cursor_location = (cursor_pos[0], cursor_pos[1]+len(text))
        self.notify('Text pasted into text area!')


if __name__ == '__main__':
    app = TuidoApp()
    app.run()
