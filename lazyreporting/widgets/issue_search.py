from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Label


class IssueSearch(Widget):
    """Fuzzy-filter Jira issues inline."""

    DEFAULT_CSS = """
    IssueSearch {
        height: auto;
    }
    IssueSearch ListView {
        height: 6;
        display: none;
        border: solid $accent;
    }
    IssueSearch ListView.visible {
        display: block;
    }
    """

    class IssueSelected(Message):
        def __init__(self, key: str, summary: str) -> None:
            super().__init__()
            self.key = key
            self.summary = summary

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_issues: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Issue key or summary (empty = general)", id="issue-input")
        yield ListView(id="issue-list")

    def set_issues(self, issues: list[dict]) -> None:
        self._all_issues = issues
        self._apply_filter(self.query_one("#issue-input", Input).value)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        lv = self.query_one("#issue-list", ListView)
        if lv.highlighted_child is not None:
            self._select_highlighted()
        else:
            # accept typed value as-is (for direct ticket entry)
            val = event.value.strip()
            self.post_message(self.IssueSelected(val, ""))
            self._hide_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._select_highlighted()

    def on_key(self, event) -> None:
        lv = self.query_one("#issue-list", ListView)
        inp = self.query_one("#issue-input", Input)
        if not inp.has_focus:
            return
        if event.key == "down" and "visible" in lv.classes:
            lv.focus()
            event.stop()
        elif event.key == "escape":
            self._hide_list()
            event.stop()

    def on_list_view_key(self, event) -> None:
        if event.key == "escape":
            self._hide_list()
            self.query_one("#issue-input", Input).focus()
            event.stop()

    def _apply_filter(self, query: str) -> None:
        lv = self.query_one("#issue-list", ListView)
        q = query.strip().lower()
        if not q:
            self._hide_list()
            return
        self._filtered = [
            i for i in self._all_issues
            if q in i["key"].lower() or q in i["summary"].lower()
        ][:10]
        lv.clear()
        for issue in self._filtered:
            lv.append(ListItem(Label(f"[bold]{issue['key']}[/]  {issue['summary'][:60]}")))
        if self._filtered:
            lv.add_class("visible")
        else:
            lv.remove_class("visible")

    def _select_highlighted(self) -> None:
        lv = self.query_one("#issue-list", ListView)
        idx = lv.index
        if idx is not None and idx < len(self._filtered):
            issue = self._filtered[idx]
            inp = self.query_one("#issue-input", Input)
            inp.value = issue["key"]
            self.post_message(self.IssueSelected(issue["key"], issue["summary"]))
            self._hide_list()
            inp.focus()

    def _hide_list(self) -> None:
        lv = self.query_one("#issue-list", ListView)
        lv.remove_class("visible")

    def clear(self) -> None:
        inp = self.query_one("#issue-input", Input)
        inp.value = ""
        self._hide_list()

    @property
    def value(self) -> str:
        return self.query_one("#issue-input", Input).value.strip()
