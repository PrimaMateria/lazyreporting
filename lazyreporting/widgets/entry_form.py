from datetime import date

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static

from .. import config as cfg
from .. import watson
from .issue_search import IssueSearch


class EntryForm(Widget):
    """Form to add a Watson time entry."""

    DEFAULT_CSS = """
    EntryForm {
        height: auto;
        padding: 0 1;
    }
    EntryForm #form-row {
        layout: horizontal;
        height: auto;
        align: left middle;
    }
    EntryForm Input {
        width: 10;
    }
    EntryForm IssueSearch {
        width: 1fr;
    }
    EntryForm #error-msg {
        color: $error;
        height: 1;
    }
    """

    class EntryAdded(Message):
        def __init__(self, day: date) -> None:
            super().__init__()
            self.day = day

    def __init__(self, app_config: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config = app_config
        self._day: date = date.today()

    def compose(self) -> ComposeResult:
        yield Static("", id="error-msg")
        with Widget(id="form-row"):
            yield Label("From ")
            yield Input(placeholder="0900", id="from-input")
            yield Label("  To ")
            yield Input(placeholder="0930", id="to-input")
            yield Label("  Issue ")
            yield IssueSearch(id="issue-search")
            yield Button("Add", id="add-btn", variant="primary")

    def set_issues(self, issues: list[dict]) -> None:
        self.query_one(IssueSearch).set_issues(issues)

    def set_day(self, day: date) -> None:
        self._day = day

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            self._submit()

    def on_key(self, event) -> None:
        if event.key == "enter":
            focused = self.app.focused
            if focused and focused.id in ("from-input", "to-input"):
                self._submit()
                event.stop()

    def _submit(self) -> None:
        from_val = self.query_one("#from-input", Input).value.strip()
        to_val = self.query_one("#to-input", Input).value.strip()
        ticket = self.query_one(IssueSearch).value

        error = self.query_one("#error-msg", Static)
        error.update("")

        try:
            project, tags = cfg.map_ticket_to_args(ticket)
            watson.add_entry(self._day, from_val, to_val, project, tags)
        except Exception as exc:
            error.update(f"[bold red]Error:[/] {exc}")
            return

        self.query_one("#from-input", Input).value = ""
        self.query_one("#to-input", Input).value = ""
        self.query_one(IssueSearch).clear()
        self.query_one("#from-input", Input).focus()
        self.post_message(self.EntryAdded(self._day))
