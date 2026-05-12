from datetime import date

from rich.align import Align
from rich.console import Group as RichGroup
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from .. import jira_client, watson


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal asking the user to confirm deletion of an entry."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #dialog {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #dialog Label {
        width: 1fr;
        content-align: center middle;
        margin-bottom: 1;
    }
    #buttons {
        layout: horizontal;
        align: center middle;
        height: auto;
    }
    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, entry: dict) -> None:
        super().__init__()
        self._entry = entry

    def compose(self) -> ComposeResult:
        start = self._entry["start"].strftime("%H:%M")
        stop = self._entry["stop"].strftime("%H:%M")
        project = self._entry["project"]
        with Static(id="dialog"):
            yield Label(f"Delete [bold]{project}[/]  {start}–{stop}?")
            with Static(id="buttons"):
                yield Button("Delete", variant="error", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class LogPanel(Widget):
    """Shows watson log for a given day. Each entry row is focusable.

    Navigation:
      up / down — move focus between rows
      d         — delete the focused entry
    """

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    can_focus = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._day: date = date.today()
        self._entries: list[dict] = []
        self._focused_idx: int = -1
        self._active: bool = False

    def compose(self) -> ComposeResult:
        yield Static("", id="log-content")

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh_for_day(self, day: date) -> None:
        self._day = day
        self._reload()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reload(self) -> None:
        self._entries = watson.get_log(self._day)
        self._focused_idx = 0 if self._entries else -1
        self._update_display()

    def _update_display(self) -> None:
        day = self._day
        content = self.query_one("#log-content", Static)

        if not self._entries:
            content.update(f"[dim]No entries for {day.isoformat()}[/]")
            return

        jira_map = {i["key"].upper(): i["summary"] for i in jira_client.load_cache()}
        total_secs = sum(
            int((e["stop"] - e["start"]).total_seconds()) for e in self._entries
        )

        renderables: list = [Text(day.strftime("%A, %d %B %Y"), style="bold")]

        for i, e in enumerate(self._entries):
            if i > 0:
                gap_secs = int((e["start"] - self._entries[i - 1]["stop"]).total_seconds())
                if gap_secs > 0:
                    gh, grem = divmod(gap_secs, 3600)
                    gm = grem // 60
                    gap_dur = f"{gh}h{gm:02d}m" if gh else f"{gm}m"
                    gap_start = self._entries[i - 1]["stop"].strftime("%H:%M")
                    gap_stop = e["start"].strftime("%H:%M")
                    renderables.append(
                        Text(f"  {gap_start} – {gap_stop}  {gap_dur}", style="dim")
                    )

            duration = int((e["stop"] - e["start"]).total_seconds())
            fraction = duration / total_secs if total_secs else 0
            renderables.append(self._build_card(e, i == self._focused_idx, fraction, jira_map))

        th, trem = divmod(total_secs, 3600)
        tm = trem // 60
        renderables.append(Text(f"Total: {th}h{tm:02d}m", style="bold"))
        content.update(RichGroup(*renderables))

    def _build_card(self, e: dict, is_focused: bool, fraction: float, jira_map: dict) -> Panel:
        start = e["start"].strftime("%H:%M")
        stop = e["stop"].strftime("%H:%M")
        duration = int((e["stop"] - e["start"]).total_seconds())
        h, rem = divmod(duration, 3600)
        m = rem // 60
        dur_str = f"{h}h{m:02d}m" if h else f"{m}m"
        project = e["project"]
        tags = e["tags"]

        jira_key = next(
            (t for t in tags if t.upper().startswith(("DATAINT-", "FINAPI-"))), None
        )
        other_tags = [t for t in tags if t != jira_key]

        bar_width = 20
        filled = round(fraction * bar_width)
        pct = round(fraction * 100)

        # Left column: time period, vertically centered
        time_col = Text(justify="center")
        time_col.append(start, style="bold cyan")
        time_col.append("\n  –  \n", style="dim")
        time_col.append(stop, style="bold cyan")

        # Right column rows
        right_rows: list = []

        # Row 1: progress bar + duration + percent
        row1 = Text()
        row1.append("█" * filled, style="green")
        row1.append("░" * (bar_width - filled), style="bright_black")
        row1.append(f"  {dur_str}", style="bold green")
        row1.append(f" ({pct}%)", style="dim green")
        right_rows.append(row1)

        # Row 2: jira key + summary (or empty if no jira)
        if jira_key:
            summary = jira_map.get(jira_key.upper(), "")
            row3 = Text()
            row3.append(jira_key, style="bold magenta")
            if summary:
                row3.append(f"  {summary}")
            right_rows.append(row3)
        else:
            right_rows.append(Text(""))

        # Row 3: project + tags, all dark grey
        row4 = Text()
        row4.append(project, style="bright_black")
        if other_tags:
            row4.append("  +" + " +".join(other_tags), style="bright_black")
        right_rows.append(row4)

        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="center", vertical="middle", min_width=7)
        grid.add_column(ratio=1)
        grid.add_row(time_col, RichGroup(*right_rows))

        border_style = "yellow" if (is_focused and self._active) else "bright_black"
        return Panel(grid, border_style=border_style, padding=(0, 1))

    def _clamp(self, idx: int) -> int:
        if not self._entries:
            return -1
        return max(0, min(idx, len(self._entries) - 1))

    # ── Key handling ──────────────────────────────────────────────────────────

    def on_focus(self) -> None:
        self._active = True
        self._update_display()

    def on_blur(self) -> None:
        self._active = False
        self._update_display()

    def on_key(self, event) -> None:
        if event.key == "up":
            self._focused_idx = self._clamp(self._focused_idx - 1)
            self._update_display()
            event.stop()
        elif event.key == "down":
            self._focused_idx = self._clamp(self._focused_idx + 1)
            self._update_display()
            event.stop()
        elif event.key == "d" and self._focused_idx >= 0:
            self._delete_focused()
            event.stop()

    def _delete_focused(self) -> None:
        if not self._entries or self._focused_idx < 0:
            return
        entry = self._entries[self._focused_idx]

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                watson.remove_entry(entry["id"])
            except Exception:
                return
            self._entries.pop(self._focused_idx)
            self._focused_idx = self._clamp(self._focused_idx)
            self._update_display()

        self.app.push_screen(ConfirmDeleteScreen(entry), _on_confirm)
