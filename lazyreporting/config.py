import os
from pathlib import Path

import yaml


def _default_config_path() -> Path:
    return Path.home() / ".config" / "lazyreporting" / "config.yaml"


def load() -> dict:
    path = Path(os.environ.get("LAZYREPORTING_CONFIG", _default_config_path()))
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
            "Please add 'email' and 'apiToken' under the jira section."
        )


def get_jira_api_token(cfg: dict) -> str:
    try:
        return cfg["jira"]["apiToken"]
    except KeyError:
        raise KeyError(
            "Missing jira.apiToken in config. "
            "Generate one at https://id.atlassian.com/manage-profile/security/api-tokens"
        )


def get_jira_projects(cfg: dict) -> list[str]:
    try:
        return cfg["jira"]["projects"]
    except KeyError:
        raise KeyError("Missing jira.projects in config (list of Jira project keys).")


def get_jira_label(cfg: dict) -> str | None:
    return cfg.get("jira", {}).get("label")


def map_ticket_to_args(ticket: str, cfg: dict) -> tuple[str, list[str]]:
    """Return (watson_project, tags) for a given Jira ticket key, using config mappings."""
    watson_cfg = cfg.get("watson", {})
    mappings = watson_cfg.get("mappings", [])
    default = watson_cfg.get("default", {"project": "default", "tags": ["other"]})

    if not ticket:
        return (default["project"], list(default.get("tags", ["other"])))

    for mapping in mappings:
        prefix = mapping.get("prefix", "")
        if prefix and ticket.upper().startswith(prefix.upper()):
            tags = list(mapping.get("tags", [])) + [ticket]
            return (mapping["project"], tags)

    # fallback: use default project, treat as sprint work
    return (default["project"], ["sprint", ticket])
