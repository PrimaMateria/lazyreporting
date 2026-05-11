"""
lazyreporting — TUI for logging time entries via Watson with Jira issue lookup.

Layout:
  Left column (2fr):  weekly calendar (top) + daily Watson log (bottom)
  Right column (3fr): entry form with full-width live Jira issue list

Pane navigation:
  Escape  — leave current input, enter pane-select mode
  h/l     — move left/right between columns
  j/k     — move up/down within left column
  Enter   — enter the highlighted pane
"""

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

# Ordered pane IDs used for navigation.
_PANES = ["calendar-pane", "log-pane", "entry-pane"]

# Spatial vim-key transitions: (current_pane, key) -> next_pane
_NAV = {
    ("calendar-pane", "j"): "log-pane",
    ("calendar-pane", "l"): "entry-pane",
    ("log-pane",      "k"): "calendar-pane",
    ("log-pane",      "l"): "entry-pane",
    ("entry-pane",    "h"): "calendar-pane",
}


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
    #left-pane {
        width: 2fr;
        layout: vertical;
    }
    /* Layout-only rules for each pane (no border here to avoid specificity conflicts) */
    #calendar-pane {
        height: auto;
        padding: 0 1;
    }
    #log-pane {
        height: 1fr;
    }
    #entry-pane {
        width: 3fr;
        padding: 0 1;
    }
    /* Border states — use .pane class for default grey so state classes can override */
    .pane              { border: solid $panel; }
    .pane.nav-selected { border: solid $warning; }
    .pane.pane-active  { border: solid $success; }
    /* Reserve border space so focus highlight doesn't cause layout shifts */
    Input {
        border: tall transparent;
    }
    ListView {
        border: solid transparent;
    }
    CalendarWidget {
        border: solid transparent;
    }
    LogPanel {
        border: solid transparent;
    }
    /* Focused widgets inside a pane: yellow */
    Input:focus {
        border: tall $warning;
    }
    ListView:focus {
        border: solid $warning;
    }
    CalendarWidget:focus {
        border: solid $warning;
    }
    LogPanel:focus {
        border: solid $warning;
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
        self._nav_mode = False
        self._nav_pane = "entry-pane"
        self._active_pane = "entry-pane"  # pane currently being interacted with

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-row"):
            with Vertical(id="left-pane"):
                with Vertical(id="calendar-pane", classes="pane"):
                    yield Static("[bold]Calendar[/]")
                    yield CalendarWidget()
                with Vertical(id="log-pane", classes="pane"):
                    yield Static("[bold]Log[/]")
                    yield LogPanel(id="log-panel")
            with Vertical(id="entry-pane", classes="pane"):
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

        # Mark and focus entry pane as the initially active pane
        self._set_active_pane("entry-pane")
        self._focus_pane("entry-pane")

    # ── Pane navigation ──────────────────────────────────────────────────────

    def on_key(self, event) -> None:
        if event.key == "escape":
            if self._nav_mode:
                # Second Escape cancels nav mode, restores focus to active pane.
                self._exit_nav_mode(enter=False)
            else:
                self._enter_nav_mode()
            event.stop()
            return

        if not self._nav_mode:
            return

        # In nav mode no widget has focus, so all keys arrive here unfiltered.
        if event.key in ("h", "j", "k", "l"):
            next_pane = _NAV.get((self._nav_pane, event.key))
            if next_pane:
                self._set_nav_pane(next_pane)
            event.stop()
        elif event.key == "enter":
            self._exit_nav_mode(enter=True)
            event.stop()

    def _enter_nav_mode(self) -> None:
        # Detect which pane currently contains the focused widget.
        focused = self.focused
        if focused is not None:
            for pane_id in _PANES:
                pane = self.query_one(f"#{pane_id}")
                if focused in pane.query("*") or focused is pane:
                    self._nav_pane = pane_id
                    break

        self._nav_mode = True
        # Remove focus from all widgets so nav keys aren't swallowed by inputs.
        self.set_focus(None)
        # Strip active (green) from all panes — nav-selected (yellow) takes over.
        for pid in _PANES:
            self.query_one(f"#{pid}").remove_class("pane-active")
        self._highlight_pane(self._nav_pane)
        self.query_one("#status-bar", Static).update(
            "[yellow]NAV[/]  h/l ←→ columns   j/k ↑↓ rows   Enter: enter   Esc: cancel"
        )

    def _exit_nav_mode(self, enter: bool) -> None:
        self._nav_mode = False
        # Clear nav highlight from all panes.
        for pid in _PANES:
            self.query_one(f"#{pid}").remove_class("nav-selected")
        if enter:
            self._set_active_pane(self._nav_pane)
            self._focus_pane(self._nav_pane)
        else:
            # Cancelled — restore previously active pane without changing it.
            self._set_active_pane(self._active_pane)
            self._focus_pane(self._active_pane)
        self.query_one("#status-bar", Static).update("")

    def _set_nav_pane(self, pane_id: str) -> None:
        # Previous nav pane goes back to plain grey (no class).
        self.query_one(f"#{self._nav_pane}").remove_class("nav-selected")
        self._nav_pane = pane_id
        self.query_one(f"#{pane_id}").add_class("nav-selected")

    def _highlight_pane(self, pane_id: str) -> None:
        for pid in _PANES:
            self.query_one(f"#{pid}").remove_class("nav-selected")
        self.query_one(f"#{pane_id}").add_class("nav-selected")

    def _set_active_pane(self, pane_id: str) -> None:
        """Mark a pane as active (green border), clearing the previous one."""
        for pid in _PANES:
            self.query_one(f"#{pid}").remove_class("pane-active")
        self.query_one(f"#{pane_id}").add_class("pane-active")
        self._active_pane = pane_id

    def _focus_pane(self, pane_id: str) -> None:
        """Give keyboard focus to the primary widget inside a pane."""
        if pane_id == "calendar-pane":
            self.query_one(CalendarWidget).focus()
        elif pane_id == "log-pane":
            self.query_one(LogPanel).focus()
        elif pane_id == "entry-pane":
            self.query_one(EntryForm).query_one("#from-input").focus()

    # ── Event handlers ───────────────────────────────────────────────────────

    def on_calendar_widget_day_selected(self, event: CalendarWidget.DaySelected) -> None:
        self.query_one(LogPanel).refresh_for_day(event.day)
        self.query_one(EntryForm).set_day(event.day)

    def on_entry_form_entry_added(self, event: EntryForm.EntryAdded) -> None:
        self.query_one(LogPanel).refresh_for_day(event.day)

    def _fetch_issues_worker(self) -> None:
        try:
            server = cfg.get_jira_server(self._app_config)
            email = cfg.get_jira_email(self._app_config)
            api_token = cfg.get_jira_api_token(self._app_config)
            issues = jira_client.fetch_issues(server, email, api_token)
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
