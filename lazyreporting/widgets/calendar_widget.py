from datetime import date, timedelta

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class CalendarWidget(Widget):
    """Week calendar — navigate with left/right (days) and [ / ] (weeks)."""

    DEFAULT_CSS = """
    CalendarWidget {
        height: auto;
        padding: 0 1;
    }
    """

    class DaySelected(Message):
        def __init__(self, day: date) -> None:
            super().__init__()
            self.day = day

    selected: reactive[date] = reactive(date.today)

    def compose(self) -> ComposeResult:
        yield Static(id="cal-display")

    def on_mount(self) -> None:
        self._render_calendar()

    def watch_selected(self, _: date) -> None:
        self._render_calendar()
        self.post_message(self.DaySelected(self.selected))

    def _week_start(self, d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _render_calendar(self) -> None:
        today = date.today()
        ws = self._week_start(self.selected)
        days = [ws + timedelta(days=i) for i in range(7)]
        headers = "  ".join(f"{'MTWTFSS'[i]:>2}" for i in range(7))
        cells = []
        for d in days:
            num = f"{d.day:>2}"
            if d == self.selected:
                num = f"[bold reverse]{num}[/]"
            elif d == today:
                num = f"[bold green]{num}[/]"
            cells.append(num)
        row = "  ".join(cells)
        month = ws.strftime("%B %Y")
        display = self.query_one("#cal-display", Static)
        display.update(f"[bold]{month}[/]\n{headers}\n{row}\n\n[dim]← →  days    [ ]  weeks[/]")

    def on_key(self, event) -> None:
        key = event.key
        if key == "left":
            self.selected = self.selected - timedelta(days=1)
            event.stop()
        elif key == "right":
            self.selected = self.selected + timedelta(days=1)
            event.stop()
        elif key == "left_square_bracket":
            self.selected = self.selected - timedelta(weeks=1)
            event.stop()
        elif key == "right_square_bracket":
            self.selected = self.selected + timedelta(weeks=1)
            event.stop()
        elif key == "t":
            # Jump to today
            self.selected = date.today()
            event.stop()
