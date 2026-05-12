import re
from collections import defaultdict
from datetime import date

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from .. import watson

_JIRA_RE = re.compile(r"^[A-Z]+-\d+$")


def _fmt_duration(seconds: float) -> str:
    total = int(seconds)
    if total < 60:
        return "< 1m"
    hours, mins = divmod(total // 60, 60)
    if hours and mins:
        return f"{hours}h {mins:02d}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def _build_summary(entries: list[dict], issue_titles: dict[str, str]) -> str:
    if not entries:
        return "No entries logged."

    totals: dict[str | None, float] = defaultdict(float)
    for e in entries:
        key = next((t for t in e.get("tags", []) if _JIRA_RE.match(t)), None)
        duration = (e["stop"] - e["start"]).total_seconds()
        totals[key] += duration

    total_secs = sum(totals.values())

    groups = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    parts = []
    for key, secs in groups:
        if key:
            title = issue_titles.get(key)
            label = f"{key}: {title}" if title else key
        else:
            label = "general work"
        parts.append(f"{label} ({_fmt_duration(secs)})")

    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = f"{parts[0]} and {parts[1]}"
    else:
        body = ", ".join(parts[:-1]) + f", and {parts[-1]}"

    return f"Worked on {body}. Total: {_fmt_duration(total_secs)}."


class SummaryPanel(Widget):
    """Auto-generated standup summary for the selected day."""

    DEFAULT_CSS = """
    SummaryPanel {
        height: auto;
        padding: 0 1;
    }
    """

    CAN_FOCUS = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._day: date = date.today()
        self._issue_titles: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Static("No entries logged.", id="summary-text")

    def set_issues(self, issues: list[dict]) -> None:
        self._issue_titles = {i["key"]: i["summary"] for i in issues}
        self._redraw()

    def refresh_for_day(self, day: date) -> None:
        self._day = day
        self._redraw()

    def _redraw(self) -> None:
        entries = watson.get_log(self._day)
        self.query_one("#summary-text", Static).update(
            _build_summary(entries, self._issue_titles)
        )
