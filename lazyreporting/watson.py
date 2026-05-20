import json
import subprocess
from datetime import date, datetime


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def get_log(day: date) -> list[dict]:
    date_str = day.isoformat()
    try:
        raw = _run(["watson", "log", "--json", "-f", date_str, "-t", date_str])
    except subprocess.CalledProcessError:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    entries = []
    for frame in data:
        start = datetime.fromisoformat(frame["start"])
        stop = datetime.fromisoformat(frame["stop"])
        entries.append(
            {
                "id": frame["id"],
                "project": frame["project"],
                "tags": frame["tags"],
                "start": start,
                "stop": stop,
            }
        )
    entries.sort(key=lambda e: e["start"])
    return entries


def add_entry(
    day: date,
    from_hhmm: str,
    to_hhmm: str,
    project: str,
    tags: list[str],
) -> None:
    from_dt = datetime.fromisoformat(f"{day.isoformat()}T{_parse_hhmm(from_hhmm)}")
    to_dt = datetime.fromisoformat(f"{day.isoformat()}T{_parse_hhmm(to_hhmm)}")
    tag_args = [f"+{t}" for t in tags]
    _run(
        [
            "watson",
            "add",
            "-f",
            from_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "-t",
            to_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            project,
            *tag_args,
        ]
    )


def sync_jira(from_days: int | None = None) -> str:
    cmd = ["watson-jira", "sync"]
    if from_days is not None:
        cmd += ["--from", str(from_days)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


def remove_entry(frame_id: str) -> None:
    _run(["watson", "remove", "--force", frame_id])


def _parse_hhmm(value: str) -> str:
    """Accept '0900', '09:00', '900' and return 'HH:MM:00'."""
    v = value.strip().replace(":", "")
    if len(v) == 3:
        v = "0" + v
    if len(v) != 4 or not v.isdigit():
        raise ValueError(f"Invalid time: {value!r}")
    return f"{v[:2]}:{v[2:]}:00"
