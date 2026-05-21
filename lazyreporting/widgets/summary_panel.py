import re
from collections import defaultdict
from datetime import date

from rich.console import Group as RichGroup
from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from .. import watson

_JIRA_RE = re.compile(r"^[A-Z]+-\d+$")
_BAR_WIDTH = 24
# Fixed chars per row: "  " + bar(24) + "  " + duration(8) + " (100%)"(7)
_ROW_FIXED = 43


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


def _build_chart(entries: list[dict], issue_titles: dict[str, str], label_width: int):
    if not entries:
        return Text("No entries logged.", style="dim")

    sorted_entries = sorted(entries, key=lambda e: e["start"])
    span_start = sorted_entries[0]["start"]
    span_end = sorted_entries[-1]["stop"]
    total_span = (span_end - span_start).total_seconds()
    if total_span <= 0:
        return Text("No time span.", style="dim")

    totals: dict[str | None, float] = defaultdict(float)
    for e in sorted_entries:
        key = next((t for t in e.get("tags", []) if _JIRA_RE.match(t)), None)
        totals[key] += (e["stop"] - e["start"]).total_seconds()

    logged_secs = sum(totals.values())
    unlogged_secs = max(0.0, total_span - logged_secs)

    def _make_label(key: str | None) -> str:
        if key is None:
            return "general"
        title = issue_titles.get(key, key)
        return title if len(title) <= label_width else title[:label_width - 1] + "…"

    # rows: (label, secs, bar_color, label_style)
    rows: list[tuple[str, float, str, str]] = []
    for key, secs in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        rows.append((_make_label(key), secs, "green", "bold"))

    if unlogged_secs >= 60:
        rows.append(("unlogged", unlogged_secs, "bright_black", "dim"))

    if not rows:
        return Text("No entries logged.", style="dim")

    max_label_len = max(len(r[0]) for r in rows)

    renderables = []
    for label, secs, bar_color, label_style in rows:
        frac = secs / total_span
        filled = round(frac * _BAR_WIDTH)
        pct = round(frac * 100)

        row = Text()
        row.append(label.ljust(max_label_len), style=label_style)
        row.append("  ")
        row.append("█" * filled, style=bar_color)
        row.append("░" * (_BAR_WIDTH - filled), style="bright_black")
        dur_style = f"bold {bar_color}" if label_style == "bold" else "dim"
        row.append(f"  {_fmt_duration(secs)}", style=dur_style)
        row.append(f" ({pct}%)", style="dim")
        renderables.append(row)

    renderables.append(Text(""))
    renderables.append(Text(f"Span: {_fmt_duration(total_span)}", style="dim"))

    return RichGroup(*renderables)


class SummaryPanel(Widget):
    """Time distribution bar chart for the selected day."""

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

    def on_resize(self, event) -> None:
        self._redraw()

    def _label_width(self) -> int:
        # padding: 0 1 consumes 2 chars; subtract fixed row overhead
        available = self.size.width - 2 - _ROW_FIXED
        return max(8, available)

    def _redraw(self) -> None:
        entries = watson.get_log(self._day)
        self.query_one("#summary-text", Static).update(
            _build_chart(entries, self._issue_titles, self._label_width())
        )
