#!/usr/bin/env python3
"""
Claude Code stats reader.

Walks ~/.claude/projects/*/*.jsonl, extracts today's activity:
  - Sessions: distinct sessionIds with activity today
  - Tokens: input/output/cache totals across assistant messages
  - Tools: tool_use counts by tool name
  - Skills: Skill invocations by skill name
  - Agents: Agent (sub-agent) invocations by subagent_type
  - Projects: per-project token totals (top N)
  - Models: model usage distribution

Designed to be cheap: only opens files modified in the last 30 hours,
and stops parsing each file as soon as it sees a timestamp older than
today's local midnight.
"""
import os
import json
import glob
from datetime import datetime, time as dtime
from collections import defaultdict

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")


def _today_start_iso():
    """ISO timestamp for today 00:00 local time, with timezone."""
    now = datetime.now().astimezone()
    midnight = datetime.combine(now.date(), dtime.min, tzinfo=now.tzinfo)
    return midnight


def _decode_project_path(folder_name):
    """Reverse the dash-encoded folder names back to a readable label.

    Folders look like:
      -Users-samimeseik-Library-...-Viral-Solution
    We just want the last segment as a label.
    """
    parts = folder_name.lstrip("-").split("-")
    # Take the last 2-3 readable segments, skip Library/CloudStorage/GoogleDrive prefixes
    if not parts:
        return folder_name
    # Heuristic: last segment that looks like a real project name
    skip = {"Users", "Library", "CloudStorage", "GoogleDrive", "My", "Drive"}
    # walk from end, take first segment not in skip
    label_parts = []
    for p in reversed(parts):
        if p in skip or "@" in p or "." in p:
            if label_parts:
                break
            continue
        label_parts.append(p)
        if len(label_parts) >= 2:
            break
    if not label_parts:
        return parts[-1] if parts else folder_name
    return " ".join(reversed(label_parts))


def _iter_recent_files(max_age_hours=30):
    """Yield (project_folder, file_path) for jsonl files modified recently."""
    if not os.path.isdir(PROJECTS_DIR):
        return
    cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
    for project in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, project)
        if not os.path.isdir(project_path):
            continue
        for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
            try:
                if os.path.getmtime(fp) >= cutoff:
                    yield project, fp
            except OSError:
                continue


def _process_assistant_message(record, stats, project, today_start):
    """Process an `assistant`-type record. Mutates stats dict in place."""
    msg = record.get("message") or {}
    if not isinstance(msg, dict):
        return

    # Tokens
    usage = msg.get("usage") or {}
    if isinstance(usage, dict):
        stats["tokens"]["input"] += int(usage.get("input_tokens", 0) or 0)
        stats["tokens"]["output"] += int(usage.get("output_tokens", 0) or 0)
        stats["tokens"]["cache_read"] += int(usage.get("cache_read_input_tokens", 0) or 0)
        stats["tokens"]["cache_create"] += int(usage.get("cache_creation_input_tokens", 0) or 0)
        # Per-project token totals
        total = (
            int(usage.get("input_tokens", 0) or 0)
            + int(usage.get("output_tokens", 0) or 0)
            + int(usage.get("cache_creation_input_tokens", 0) or 0)
        )
        if total:
            stats["projects"][project] += total

    # Model usage
    model = msg.get("model")
    if model:
        # Trim long names like "claude-sonnet-4-6" → "sonnet-4-6"
        short = model.replace("claude-", "")
        stats["models"][short] += 1

    # Tools / Skills / Agents (inspect content array)
    content = msg.get("content") or []
    if not isinstance(content, list):
        return
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get("type") != "tool_use":
            continue
        tool_name = c.get("name") or ""
        stats["tools"][tool_name] += 1
        # Skill / Agent attribution
        inp = c.get("input") or {}
        if not isinstance(inp, dict):
            continue
        if tool_name == "Skill":
            skill = inp.get("skill")
            if skill:
                stats["skills"][skill] += 1
        elif tool_name == "Agent":
            sub = inp.get("subagent_type")
            if sub:
                stats["agents"][sub] += 1


def collect_stats():
    """Walk all recent jsonl files and produce today's stats dict."""
    today_start = _today_start_iso()
    today_start_ts = today_start.timestamp()

    stats = {
        "sessions": set(),
        "messages": 0,
        "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0},
        "tools": defaultdict(int),
        "skills": defaultdict(int),
        "agents": defaultdict(int),
        "projects": defaultdict(int),
        "models": defaultdict(int),
    }

    for project, fp in _iter_recent_files():
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, json.JSONDecodeError):
                        continue

                    # Filter to today
                    ts = rec.get("timestamp")
                    if not ts:
                        continue
                    try:
                        rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if rec_dt.timestamp() < today_start_ts:
                            continue
                    except (ValueError, TypeError):
                        continue

                    rtype = rec.get("type")
                    sid = rec.get("sessionId")
                    if sid:
                        stats["sessions"].add(sid)

                    if rtype == "assistant":
                        stats["messages"] += 1
                        _process_assistant_message(rec, stats, project, today_start)
        except OSError:
            continue

    # Convert to JSON-friendly shape
    out = {
        "sessions": len(stats["sessions"]),
        "messages": stats["messages"],
        "tokens": stats["tokens"],
        "tokens_total": (
            stats["tokens"]["input"]
            + stats["tokens"]["output"]
            + stats["tokens"]["cache_create"]
        ),
        "top_tools": _top_n(stats["tools"], 5),
        "top_skills": _top_n(stats["skills"], 3),
        "top_agents": _top_n(stats["agents"], 3),
        "top_projects": _top_projects(stats["projects"], 3),
        "models": _top_n(stats["models"], 3),
        "as_of": datetime.now().astimezone().isoformat(),
    }
    return out


def _top_n(counter, n):
    items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    return [{"name": k, "count": v} for k, v in items[:n]]


def _top_projects(counter, n):
    items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    out = []
    for project_folder, tokens in items[:n]:
        out.append({
            "name": _decode_project_path(project_folder),
            "tokens": tokens,
        })
    return out


if __name__ == "__main__":
    print(json.dumps(collect_stats(), indent=2))
