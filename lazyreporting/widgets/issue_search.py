from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input


class IssueSearch(Widget):
    """Input that filters Jira issues and emits FilterChanged messages."""

    DEFAULT_CSS = """
    IssueSearch {
        height: auto;
        width: 1fr;
    }
    IssueSearch Input {
        width: 100%;
    }
    """

    class FilterChanged(Message):
        def __init__(self, issues: list[dict]) -> None:
            super().__init__()
            self.issues = issues

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_issues: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Issue key or summary (empty = general work)", id="issue-input")

    def set_issues(self, issues: list[dict]) -> None:
        self._all_issues = issues
        self._emit_filter(self.query_one("#issue-input", Input).value)

    def set_value(self, value: str) -> None:
        self.query_one("#issue-input", Input).value = value

    def focus(self, scroll_visible: bool = True) -> None:
        self.query_one("#issue-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._emit_filter(event.value)

    def _emit_filter(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            filtered = self._all_issues
        else:
            filtered = [
                i for i in self._all_issues
                if q in i["key"].lower() or q in i["summary"].lower()
            ]
        self.post_message(self.FilterChanged(filtered))

    def clear(self) -> None:
        self.query_one("#issue-input", Input).value = ""

    @property
    def value(self) -> str:
        return self.query_one("#issue-input", Input).value.strip()
