# lazyreporting

A lazygit-style terminal UI for logging time entries via [Watson](https://tailordev.github.io/Watson/) with live Jira issue lookup.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)

## What it does

- Browse a weekly calendar and see your Watson log for any day
- Search Jira issues by key or summary and attach them to time entries
- Add and delete Watson entries without leaving the terminal
- Auto-generate a standup summary ("Worked on PROJ-42: Feature X for 2h 30m…") ready to read next morning
- Sync logged time to Jira worklogs via `watson-jira`

## Prerequisites

| Tool | Purpose |
|------|---------|
| [Watson](https://tailordev.github.io/Watson/) | Local time tracker — stores frames |
| [watson-jira](https://github.com/PrimaMateria/watson-jira-next) | Syncs Watson frames to Jira worklogs |
| Python 3.11+ | Runtime |
| A Jira Cloud account with an API token | Issue lookup and sync |

## Installation

```sh
pip install .
```

This installs the `lr` command.

### Nix / NixOS

A `flake.nix` is provided. Enter the dev shell with:

```sh
nix develop
```

This drops you into a shell with Watson, watson-jira, and the Python environment ready. Use `lr` to launch.

## Configuration

**`~/.config/lazyreporting/config.yaml`** (override path with `$LAZYREPORTING_CONFIG`):

```yaml
jira:
  server: https://your-company.atlassian.net
  email: you@example.com
  apiToken: <your-api-token>       # generate at id.atlassian.com/manage-profile/security/api-tokens
  projects:                        # Jira project keys to include in issue search
    - PROJ1
    - PROJ2
  label: Frontend                  # optional — filters issues to this label only

watson:
  mappings:                        # ticket prefix → Watson project + tags
    - prefix: PROJ1
      project: myproject
      tags: [sprint]
    - prefix: PROJ2
      project: other-project
      tags: [sprint]
  default:                         # used when no ticket is given (or prefix doesn't match)
    project: myproject
    tags: [other]
```

When a ticket key is matched, it is automatically appended to `tags` so Watson frames stay linked to the Jira issue (e.g. tags become `[sprint, PROJ1-42]`).

## Usage

```sh
lr
```

### Layout

```
┌─────────────────┬──────────────────────────┐
│   Calendar      │                          │
├─────────────────│       Add Entry          │
│                 │                          │
│   Log           ├──────────────────────────┤
│                 │                          │
├─────────────────│                          │
│   Summary       │                          │
└─────────────────┴──────────────────────────┘
```

### Keyboard shortcuts

#### Pane navigation

| Key | Action |
|-----|--------|
| `Esc` | Enter nav mode (yellow borders) |
| `h` / `←` | Move left |
| `l` / `→` | Move right |
| `j` / `↓` | Move down |
| `k` / `↑` | Move up |
| `Enter` | Enter highlighted pane |
| `Esc` (again) | Cancel nav, restore previous pane |

#### Entry form (Add Entry pane)

| Key | Action |
|-----|--------|
| Type 4 digits | Auto-advance from **From** → **To** → **Issue** |
| `Enter` | Submit entry from any field |
| `↓` | Open issue list from issue field |
| `Esc` | Return focus to issue field from list |

#### Log pane

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate entries |
| `d` | Delete focused entry (confirm dialog) |

#### Global

| Key | Action |
|-----|--------|
| `r` | Refresh Jira issue cache |
| `s` | Sync Watson frames to Jira |
| `q` | Quit |

## Issue cache

Jira issues are cached at `~/.cache/lazyreporting/issues.json` with a 15-minute TTL. The cache is loaded immediately on startup so the issue list is available even without a network connection; a background fetch refreshes it on launch.

## License

MIT
