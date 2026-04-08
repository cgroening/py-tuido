import threading
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Static, TextArea, Markdown
from tuido.services.notes_service import NotesService


class NotesTab(Static):
    """
    Notes tab - side-by-side Markdown textarea and rendered preview.

    Receives a `NotesService` and wires the TextArea change event to
    the service's throttle/debounce auto-save logic.
    """
    _service: NotesService
    textarea: TextArea
    markdown: Markdown


    def __init__(self, service: NotesService, **kwargs) -> None:  # type:ignore[reportMissingParameterType]
        """Initializes the `NotesTab` with the provided `NotesService`."""
        super().__init__(**kwargs)  # type:ignore[reportMissingParameterType]
        self._service = service
        self.textarea = TextArea(
            id='notes_textarea',
            classes='notes-textarea',
            show_line_numbers=True,
        )
        self.textarea.indent_type = 'spaces'
        self.textarea.indent_width = 4
        self.markdown = Markdown(id='notes_markdown', classes='notes-markdown')

    def on_mount(self) -> None:
        """Populates the textarea with saved notes on mount."""
        self.textarea.text = self._service.get_notes()

    def compose(self) -> ComposeResult:
        with Grid():
            yield self.textarea
            yield self.markdown

    @on(TextArea.Changed)
    async def update_markdown(self, event: TextArea.Changed) -> None:
        """Syncs the markdown preview and trigger auto-save."""
        await self.query_one('#notes_markdown').update(event.text_area.text)  # type: ignore
        threading.Thread(
            target=self._service.on_text_changed,
            args=(event.text_area.text,),
            daemon=True,
        ).start()
