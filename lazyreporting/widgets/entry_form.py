from datetime import date

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from .. import config as cfg
from .. import watson
from .issue_search import IssueSearch


class EntryForm(Widget):
    """Form to add a Watson time entry."""

    DEFAULT_CSS = """
    EntryForm {
        height: 1fr;
        padding: 0 1;
        layout: vertical;
    }
    EntryForm #form-row {
        layout: horizontal;
        height: auto;
        align: left middle;
    }
    EntryForm #from-input {
        width: 11;
    }
    EntryForm #to-input {
        width: 11;
    }
    EntryForm #form-row IssueSearch {
        width: 1fr;
    }
    EntryForm #error-msg {
        color: $error;
        height: 1;
    }
    EntryForm #issue-list {
        margin-top: 1;
        padding-left: 1;
        height: 1fr;
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
        self._all_issues: list[dict] = []
        self._filtered: list[dict] = []

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
        yield ListView(id="issue-list")

    def set_config(self, app_config: dict) -> None:
        self._config = app_config

    def set_issues(self, issues: list[dict]) -> None:
        self._all_issues = issues
        self.query_one(IssueSearch).set_issues(issues)
        self._update_list(issues)

    def _update_list(self, issues: list[dict]) -> None:
        self._filtered = issues
        lv = self.query_one("#issue-list", ListView)
        lv.clear()
        for issue in issues:
            lv.append(ListItem(Label(f"[bold]{issue['key']}[/]  {issue['summary']}")))

    def on_issue_search_filter_changed(self, event: IssueSearch.FilterChanged) -> None:
        self._update_list(event.issues)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and idx < len(self._filtered):
            issue = self._filtered[idx]
            self.query_one(IssueSearch).set_value(issue["key"])
            self.query_one(IssueSearch).focus()

    def set_day(self, day: date) -> None:
        self._day = day

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            self._submit()

    def on_input_changed(self, event: Input.Changed) -> None:
        # Auto-advance focus after 4 digits so the user never needs to tab.
        if event.input.id in ("from-input", "to-input") and len(event.value) == 4:
            if event.input.id == "from-input":
                self.query_one("#to-input", Input).focus()
            else:
                self.query_one(IssueSearch).focus()

    def on_key(self, event) -> None:
        focused = self.app.focused
        # Down from issue input → move into the list for keyboard selection.
        if event.key == "down" and focused and focused.id == "issue-input":
            self.query_one("#issue-list", ListView).focus()
            event.stop()
        # Escape from list → return focus to the issue input.
        elif event.key == "escape" and focused and focused.id == "issue-list":
            self.query_one(IssueSearch).focus()
            event.stop()
        elif event.key == "enter" and focused and focused.id in ("from-input", "to-input"):
            self._submit()
            event.stop()

    def _submit(self) -> None:
        from_val = self.query_one("#from-input", Input).value.strip()
        to_val = self.query_one("#to-input", Input).value.strip()
        ticket = self.query_one(IssueSearch).value

        error = self.query_one("#error-msg", Static)
        error.update("")

        try:
            project, tags = cfg.map_ticket_to_args(ticket, self._config)
            watson.add_entry(self._day, from_val, to_val, project, tags)
        except Exception as exc:
            error.update(f"[bold red]Error:[/] {exc}")
            return

        self.query_one("#from-input", Input).value = ""
        self.query_one("#to-input", Input).value = ""
        self.query_one(IssueSearch).clear()
        self.query_one("#from-input", Input).focus()
        self.post_message(self.EntryAdded(self._day))
