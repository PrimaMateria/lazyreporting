import os
from pathlib import Path

import yaml


def _default_config_path() -> Path:
    return Path.home() / ".config" / "watson-jira" / "config.yaml"


def load() -> dict:
    path = Path(os.environ.get("WATSON_JIRA_CONFIG", _default_config_path()))
    with open(path) as f:
        return yaml.safe_load(f)


def get_jira_server(cfg: dict) -> str:
    return cfg["jira"]["server"].rstrip("/")


def get_jira_email(cfg: dict) -> str:
    try:
        return cfg["jira"]["email"]
    except KeyError:
        raise KeyError(
            "Missing jira.email in config. "
            "Please update your config with 'email' and 'api_token' fields "
            "(cookie auth is no longer supported)."
        )


def get_jira_api_token(cfg: dict) -> str:
    try:
        return cfg["jira"]["api_token"]
    except KeyError:
        raise KeyError(
            "Missing jira.api_token in config. "
            "Generate one at https://id.atlassian.com/manage-profile/security/api-tokens"
        )


def map_ticket_to_args(ticket: str) -> tuple[str, list[str]]:
    """Return (watson_project, tags) for a given Jira ticket key."""
    if not ticket:
        return ("di", ["other"])
    if ticket.upper().startswith("DATAINT"):
        return ("di", ["sprint", ticket])
    if ticket.upper().startswith("FINAPI"):
        return ("webform", ["sprint", ticket])
    # fallback: treat as DI sprint
    return ("di", ["sprint", ticket])
