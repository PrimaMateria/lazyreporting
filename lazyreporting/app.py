from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from . import config as cfg
from . import jira_client
from . import watson
from .widgets.calendar_widget import CalendarWidget
from .widgets.entry_form import EntryForm
from .widgets.log_panel import LogPanel


class LazyReporting(App):
    TITLE = "lazyreporting"
    CSS = """
    Screen {
        layout: vertical;
    }
    #top-row {
        height: 1fr;
        layout: horizontal;
    }
    #calendar-pane {
        width: 28;
        border: solid $panel;
        padding: 0 1;
    }
    #log-pane {
        width: 1fr;
        border: solid $panel;
    }
    #entry-pane {
        height: auto;
        border: solid $accent;
        padding: 0 1;
    }
    #status-bar {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("r", "refresh_issues", "Refresh issues"),
        Binding("s", "sync_jira", "Sync Jira"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._app_config: dict = {}
        self._issues: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-row"):
            with Vertical(id="calendar-pane"):
                yield Static("[bold]Calendar[/]")
                yield CalendarWidget()
            with Vertical(id="log-pane"):
                yield Static("[bold]Log[/]")
                yield LogPanel(id="log-panel")
        with Vertical(id="entry-pane"):
            yield Static("[bold]Add Entry[/]")
            yield EntryForm(app_config={}, id="entry-form")
        yield Static("Loading…", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self._app_config = cfg.load()
        except FileNotFoundError as e:
            self.query_one("#status-bar", Static).update(f"[red]Config not found: {e}[/]")
            return

        # Load cache immediately so issue list is available on startup
        cached = jira_client.load_cache()
        if cached:
            self._set_issues(cached)
            age = jira_client.cache_age_minutes()
            self.query_one("#status-bar", Static).update(
                f"Issues: {len(cached)} (cached {age}m ago) — refreshing…"
            )
        else:
            self.query_one("#status-bar", Static).update("Fetching issues…")

        self.run_worker(self._fetch_issues_worker, exclusive=True, thread=True)

        # Show today's log
        today = date.today()
        self.query_one(LogPanel).refresh_for_day(today)
        self.query_one(EntryForm).set_day(today)

    def on_calendar_widget_day_selected(self, event: CalendarWidget.DaySelected) -> None:
        self.query_one(LogPanel).refresh_for_day(event.day)
        self.query_one(EntryForm).set_day(event.day)

    def on_entry_form_entry_added(self, event: EntryForm.EntryAdded) -> None:
        self.query_one(LogPanel).refresh_for_day(event.day)

    def _fetch_issues_worker(self) -> None:
        try:
            server = cfg.get_jira_server(self._app_config)
            cookie = cfg.get_jira_cookie(self._app_config)
            issues = jira_client.fetch_issues(server, cookie)
            jira_client.save_cache(issues)
            self.call_from_thread(self._set_issues, issues)
            self.call_from_thread(
                self.query_one("#status-bar", Static).update,
                f"Issues: {len(issues)} (just updated)",
            )
        except Exception as exc:
            self.call_from_thread(
                self.query_one("#status-bar", Static).update,
                f"[red]Jira fetch failed:[/] {exc}",
            )

    def _set_issues(self, issues: list[dict]) -> None:
        self._issues = issues
        self.query_one(EntryForm).set_issues(issues)

    def action_refresh_issues(self) -> None:
        self.query_one("#status-bar", Static).update("Refreshing…")
        self.run_worker(self._fetch_issues_worker, exclusive=True, thread=True)

    def action_sync_jira(self) -> None:
        self.query_one("#status-bar", Static).update("Syncing to Jira…")
        self.run_worker(self._sync_worker, exclusive=False, thread=True)

    def _sync_worker(self) -> None:
        out = watson.sync_jira()
        msg = out.strip().split("\n")[-1] if out.strip() else "Sync done"
        self.call_from_thread(
            self.query_one("#status-bar", Static).update,
            f"[green]{msg}[/]",
        )


def run() -> None:
    LazyReporting().run()
