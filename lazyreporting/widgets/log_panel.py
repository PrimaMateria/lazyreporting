from datetime import date

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from .. import watson


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

        lines = [f"[bold]{day.strftime('%A, %d %B %Y')}[/]\n"]
        total_secs = 0

        for i, e in enumerate(self._entries):
            # Insert a grey filler for any gap between the previous entry and this one.
            if i > 0:
                gap_secs = int((e["start"] - self._entries[i - 1]["stop"]).total_seconds())
                if gap_secs > 0:
                    gh, grem = divmod(gap_secs, 3600)
                    gm = grem // 60
                    gap_dur = f"{gh}h{gm:02d}m" if gh else f"{gm}m"
                    gap_start = self._entries[i - 1]["stop"].strftime("%H:%M")
                    gap_stop = e["start"].strftime("%H:%M")
                    lines.append(
                        f" [dim]{gap_start} – {gap_stop}  {gap_dur}[/]"
                    )

            start = e["start"].strftime("%H:%M")
            stop = e["stop"].strftime("%H:%M")
            duration = int((e["stop"] - e["start"]).total_seconds())
            total_secs += duration
            h, rem = divmod(duration, 3600)
            m = rem // 60
            dur_str = f"{h}h{m:02d}m" if h else f"{m}m"
            project = e["project"]
            tags = ", ".join(e["tags"]) if e["tags"] else ""
            tag_str = f" +{tags}" if tags else ""

            if i == self._focused_idx:
                line = (
                    f"[bold reverse] {start} – {stop}  {project}{tag_str}  {dur_str} [/]"
                )
            else:
                line = (
                    f" [cyan]{start}[/] – [cyan]{stop}[/]"
                    f"  [bold]{project}[/]"
                    + (f"  [dim]+{tags}[/]" if tags else "")
                    + f"  [dim]{dur_str}[/]"
                )

            lines.append(line)

        th, trem = divmod(total_secs, 3600)
        tm = trem // 60
        lines.append(f"\n[bold]Total: {th}h{tm:02d}m[/]")
        content.update("\n".join(lines))

    def _clamp(self, idx: int) -> int:
        if not self._entries:
            return -1
        return max(0, min(idx, len(self._entries) - 1))

    # ── Key handling ──────────────────────────────────────────────────────────

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
