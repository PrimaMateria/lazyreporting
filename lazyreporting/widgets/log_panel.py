from datetime import date

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from .. import watson


class LogPanel(Widget):
    """Shows watson log for a given day. Focusable — scroll with up/down arrows."""

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    can_focus = True

    def on_key(self, event) -> None:
        if event.key == "up":
            self.scroll_up()
            event.stop()
        elif event.key == "down":
            self.scroll_down()
            event.stop()

    def compose(self) -> ComposeResult:
        yield Static("", id="log-content")

    def refresh_for_day(self, day: date) -> None:
        self._day = day
        self._reload()

    def _reload(self) -> None:
        day = getattr(self, "_day", date.today())
        entries = watson.get_log(day)
        content = self.query_one("#log-content", Static)
        if not entries:
            content.update(f"[dim]No entries for {day.isoformat()}[/]")
            return

        lines = [f"[bold]{day.strftime('%A, %d %B %Y')}[/]\n"]
        total_secs = 0
        for e in entries:
            start = e["start"].strftime("%H:%M")
            stop = e["stop"].strftime("%H:%M")
            duration = int((e["stop"] - e["start"]).total_seconds())
            total_secs += duration
            h, rem = divmod(duration, 3600)
            m = rem // 60
            dur_str = f"{h}h{m:02d}m" if h else f"{m}m"
            project = e["project"]
            tags = ", ".join(e["tags"]) if e["tags"] else ""
            tag_str = f"  [dim]+{tags}[/]" if tags else ""
            lines.append(f"[cyan]{start}[/] – [cyan]{stop}[/]  [bold]{project}[/]{tag_str}  [dim]{dur_str}[/]")

        th, trem = divmod(total_secs, 3600)
        tm = trem // 60
        lines.append(f"\n[bold]Total: {th}h{tm:02d}m[/]")
        content.update("\n".join(lines))
