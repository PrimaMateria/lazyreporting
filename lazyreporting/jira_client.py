import json
import time
from pathlib import Path

import requests

CACHE_PATH = Path.home() / ".cache" / "lazyreporting" / "issues.json"
CACHE_TTL = 900  # 15 minutes

JQL = (
    "project in (FINAPI, DATAINT) "
    "AND labels = Frontend "
    "AND (STATUS != Done OR updated > -1w) "
    "ORDER BY updated DESC"
)


def _cache_age() -> float:
    if not CACHE_PATH.exists():
        return float("inf")
    return time.time() - CACHE_PATH.stat().st_mtime


def is_stale() -> bool:
    return _cache_age() > CACHE_TTL


def cache_age_minutes() -> int:
    age = _cache_age()
    if age == float("inf"):
        return -1
    return int(age / 60)


def load_cache() -> list[dict]:
    if not CACHE_PATH.exists():
        return []
    with open(CACHE_PATH) as f:
        return json.load(f)


def save_cache(issues: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(issues, f)


def fetch_issues(server: str, email: str, api_token: str, max_results: int = 100) -> list[dict]:
    url = f"{server}/rest/api/3/search/jql"
    headers = {"Content-Type": "application/json"}
    params = {
        "jql": JQL,
        "fields": "key,summary,status,assignee",
        "maxResults": max_results,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=15, auth=(email, api_token))
    resp.raise_for_status()
    data = resp.json()
    issues = []
    for item in data.get("issues", []):
        issues.append(
            {
                "key": item["key"],
                "summary": item["fields"]["summary"],
                "status": item["fields"]["status"]["name"],
                "assignee": (item["fields"].get("assignee") or {}).get(
                    "displayName", ""
                ),
            }
        )
    return issues
