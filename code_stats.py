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
import time
from datetime import datetime, time as dtime
from collections import defaultdict

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")

# ─── API pricing (per 1M tokens, USD) ──────────────────────────────
# Source: anthropic.com/pricing (2026 rates).
# We match models by substring — "sonnet-4-6", "claude-sonnet-4-6",
# "claude-3-5-sonnet" all match the "sonnet" entry. Opus comes first
# so "claude-opus-4-7" doesn't accidentally match the sonnet rule.
PRICING = [
    # (substring, input, output, cache_read_multiplier, cache_write_multiplier)
    ("opus",       15.00, 75.00, 0.10, 1.25),
    ("sonnet",      3.00, 15.00, 0.10, 1.25),
    ("haiku",       0.80,  4.00, 0.10, 1.25),
]
DEFAULT_PRICING = ("sonnet", 3.00, 15.00, 0.10, 1.25)
# Plan prices (USD/month) — used to compute "value vs plan"
PLAN_PRICES = {
    "max":   200.0,
    "max5x": 100.0,  # Claude Max 5x ($100/mo tier)
    "pro":    20.0,
}
COST_CACHE = os.path.expanduser("~/.claude-widget/cost_cache.json")
HEATMAP_CACHE = os.path.expanduser("~/.claude-widget/heatmap_cache.json")
HEATMAP_TTL_SECONDS = 3600  # rebuild at most once per hour
HOURLY_CACHE = os.path.expanduser("~/.claude-widget/hourly_cache.json")
LEADERBOARD_CACHE = os.path.expanduser("~/.claude-widget/leaderboard_cache.json")


def _today_start_iso():
    """ISO timestamp for today 00:00 local time, with timezone."""
    now = datetime.now().astimezone()
    midnight = datetime.combine(now.date(), dtime.min, tzinfo=now.tzinfo)
    return midnight


def _days_ago_iso(days):
    """ISO timestamp for `days` days ago at 00:00 local time."""
    from datetime import timedelta
    now = datetime.now().astimezone()
    cutoff_date = now.date() - timedelta(days=days - 1)  # include today + (days-1) prev
    return datetime.combine(cutoff_date, dtime.min, tzinfo=now.tzinfo)


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


def compute_heatmap(days=365):
    """Walk ALL .jsonl files within `days`, bin tokens by local date.

    Returns dict:
      {
        "days": days,
        "buckets": [int, ...],   # length=days, [oldest ... today]
        "max":    int,           # peak day for color scaling
        "total":  int,           # sum across the window
        "active_days": int,      # count of non-zero days
        "as_of":  ISO8601
      }

    Result is cached for HEATMAP_TTL_SECONDS to keep refresh under 50ms.
    """
    # Try cache first
    try:
        if os.path.exists(HEATMAP_CACHE):
            age = time.time() - os.path.getmtime(HEATMAP_CACHE)
            if age < HEATMAP_TTL_SECONDS:
                with open(HEATMAP_CACHE, "r") as f:
                    return json.load(f)
    except Exception:
        pass

    from datetime import timedelta
    today = datetime.now().astimezone()
    cutoff_dt = datetime.combine(
        (today - timedelta(days=days - 1)).date(),
        dtime.min, tzinfo=today.tzinfo,
    )
    cutoff_ts = cutoff_dt.timestamp()
    file_cutoff_ts = datetime.now().timestamp() - ((days + 2) * 86400)

    buckets = [0] * days

    if not os.path.isdir(PROJECTS_DIR):
        out = {
            "days": days, "buckets": buckets, "max": 0,
            "total": 0, "active_days": 0,
            "as_of": today.isoformat(),
        }
        return out

    for project in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, project)
        if not os.path.isdir(project_path):
            continue
        for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
            try:
                if os.path.getmtime(fp) < file_cutoff_ts:
                    continue
            except OSError:
                continue
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
                        if rec.get("type") != "assistant":
                            continue
                        ts = rec.get("timestamp")
                        if not ts:
                            continue
                        try:
                            rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            rec_ts = rec_dt.timestamp()
                        except (ValueError, TypeError):
                            continue
                        if rec_ts < cutoff_ts:
                            continue
                        msg = rec.get("message") or {}
                        if not isinstance(msg, dict):
                            continue
                        usage = msg.get("usage") or {}
                        if not isinstance(usage, dict):
                            continue
                        total = (
                            int(usage.get("input_tokens", 0) or 0)
                            + int(usage.get("output_tokens", 0) or 0)
                            + int(usage.get("cache_creation_input_tokens", 0) or 0)
                        )
                        if not total:
                            continue
                        days_back = (today.date() - rec_dt.astimezone().date()).days
                        idx = (days - 1) - days_back
                        if 0 <= idx < days:
                            buckets[idx] += total
            except OSError:
                continue

    out = {
        "days": days,
        "buckets": buckets,
        "max": max(buckets) if buckets else 0,
        "total": sum(buckets),
        "active_days": sum(1 for b in buckets if b > 0),
        "as_of": today.isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(HEATMAP_CACHE), exist_ok=True)
        with open(HEATMAP_CACHE, "w") as f:
            json.dump(out, f)
    except Exception:
        pass
    return out


def _price_for_model(model_name):
    """Return (input, output, cache_read_mult, cache_write_mult) for a model name."""
    if not model_name:
        return DEFAULT_PRICING[1:]
    lower = str(model_name).lower()
    for sub, inp, outp, cr, cw in PRICING:
        if sub in lower:
            return (inp, outp, cr, cw)
    return DEFAULT_PRICING[1:]


def compute_cost(days=30):
    """API-equivalent cost over the last `days` days, broken down by model.

    Returns:
      {
        "days": int,
        "month_to_date": float,    # cost since the 1st of the current month
        "last_30d":      float,    # full window cost
        "projected_month": float,  # extrapolated full-month cost
        "by_model": [{"name", "tokens", "cost"}],
        "savings_vs_max": float,   # max(0, last_30d - 200)
        "as_of": ISO8601,
      }

    Cached for 1 hour like heatmap.
    """
    try:
        if os.path.exists(COST_CACHE):
            age = time.time() - os.path.getmtime(COST_CACHE)
            if age < HEATMAP_TTL_SECONDS:
                with open(COST_CACHE, "r") as f:
                    return json.load(f)
    except Exception:
        pass

    from datetime import timedelta
    today = datetime.now().astimezone()
    month_start = datetime.combine(
        today.date().replace(day=1), dtime.min, tzinfo=today.tzinfo,
    )
    cutoff_dt = datetime.combine(
        (today - timedelta(days=days - 1)).date(),
        dtime.min, tzinfo=today.tzinfo,
    )
    cutoff_ts = cutoff_dt.timestamp()
    month_start_ts = month_start.timestamp()
    file_cutoff_ts = datetime.now().timestamp() - ((days + 2) * 86400)

    by_model = defaultdict(lambda: {
        "input": 0, "output": 0, "cache_read": 0, "cache_create": 0
    })
    month_cost_acc = 0.0
    window_cost_acc = 0.0

    if os.path.isdir(PROJECTS_DIR):
        for project in os.listdir(PROJECTS_DIR):
            project_path = os.path.join(PROJECTS_DIR, project)
            if not os.path.isdir(project_path):
                continue
            for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
                try:
                    if os.path.getmtime(fp) < file_cutoff_ts:
                        continue
                except OSError:
                    continue
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
                            if rec.get("type") != "assistant":
                                continue
                            ts = rec.get("timestamp")
                            if not ts:
                                continue
                            try:
                                rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                rec_ts = rec_dt.timestamp()
                            except (ValueError, TypeError):
                                continue
                            if rec_ts < cutoff_ts:
                                continue
                            msg = rec.get("message") or {}
                            if not isinstance(msg, dict):
                                continue
                            usage = msg.get("usage") or {}
                            if not isinstance(usage, dict):
                                continue
                            model = msg.get("model") or "unknown"
                            inp_t = int(usage.get("input_tokens", 0) or 0)
                            out_t = int(usage.get("output_tokens", 0) or 0)
                            cr_t  = int(usage.get("cache_read_input_tokens", 0) or 0)
                            cw_t  = int(usage.get("cache_creation_input_tokens", 0) or 0)
                            if not (inp_t or out_t or cr_t or cw_t):
                                continue

                            inp_p, out_p, cr_mult, cw_mult = _price_for_model(model)
                            line_cost = (
                                inp_t * inp_p / 1_000_000 +
                                out_t * out_p / 1_000_000 +
                                cr_t  * inp_p * cr_mult / 1_000_000 +
                                cw_t  * inp_p * cw_mult / 1_000_000
                            )

                            window_cost_acc += line_cost
                            if rec_ts >= month_start_ts:
                                month_cost_acc += line_cost

                            slot = by_model[model]
                            slot["input"]        += inp_t
                            slot["output"]       += out_t
                            slot["cache_read"]   += cr_t
                            slot["cache_create"] += cw_t
                            slot["cost"] = slot.get("cost", 0.0) + line_cost
                except OSError:
                    continue

    # Per-model totals
    by_model_out = []
    for model, agg in sorted(by_model.items(), key=lambda kv: kv[1].get("cost", 0), reverse=True):
        tokens = agg["input"] + agg["output"] + agg["cache_create"]
        short = model.replace("claude-", "")
        by_model_out.append({
            "name":   short,
            "tokens": tokens,
            "cost":   round(agg.get("cost", 0.0), 2),
        })

    # Projected full-month cost: scale month_to_date by (days_in_month / day_of_month)
    days_passed = today.day
    # last day of current month
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    days_in_month = (next_month - timedelta(days=1)).day
    projected = (
        month_cost_acc / max(days_passed, 1) * days_in_month
        if month_cost_acc > 0 else 0.0
    )

    out = {
        "days": days,
        "month_to_date":    round(month_cost_acc, 2),
        "last_30d":         round(window_cost_acc, 2),
        "projected_month":  round(projected, 2),
        "by_model":         by_model_out[:5],
        "savings_vs_max":   round(max(0, window_cost_acc - PLAN_PRICES["max"]), 2),
        "as_of":            today.isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(COST_CACHE), exist_ok=True)
        with open(COST_CACHE, "w") as f:
            json.dump(out, f)
    except Exception:
        pass
    return out


def compute_leaderboard(days=30):
    """30-day Skills + Agents leaderboard.

    Returns:
      {
        "days": int,
        "skills": [{"name", "count", "share"}],   # top 5 by count
        "agents": [{"name", "count", "share"}],   # top 5 by count
        "tools":  [{"name", "count", "share"}],   # top 5 — for context
        "totals": {"skills": int, "agents": int, "tools": int},
        "as_of":  ISO8601
      }

    Cached identically to heatmap (1-hour TTL).
    """
    try:
        if os.path.exists(LEADERBOARD_CACHE):
            age = time.time() - os.path.getmtime(LEADERBOARD_CACHE)
            if age < HEATMAP_TTL_SECONDS:
                with open(LEADERBOARD_CACHE, "r") as f:
                    return json.load(f)
    except Exception:
        pass

    from datetime import timedelta
    today = datetime.now().astimezone()
    cutoff_dt = datetime.combine(
        (today - timedelta(days=days - 1)).date(),
        dtime.min, tzinfo=today.tzinfo,
    )
    cutoff_ts = cutoff_dt.timestamp()
    file_cutoff_ts = datetime.now().timestamp() - ((days + 2) * 86400)

    skills = defaultdict(int)
    agents = defaultdict(int)
    tools = defaultdict(int)

    if os.path.isdir(PROJECTS_DIR):
        for project in os.listdir(PROJECTS_DIR):
            project_path = os.path.join(PROJECTS_DIR, project)
            if not os.path.isdir(project_path):
                continue
            for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
                try:
                    if os.path.getmtime(fp) < file_cutoff_ts:
                        continue
                except OSError:
                    continue
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
                            if rec.get("type") != "assistant":
                                continue
                            ts = rec.get("timestamp")
                            if not ts:
                                continue
                            try:
                                rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                if rec_dt.timestamp() < cutoff_ts:
                                    continue
                            except (ValueError, TypeError):
                                continue
                            msg = rec.get("message") or {}
                            content = msg.get("content") if isinstance(msg, dict) else None
                            if not isinstance(content, list):
                                continue
                            for c in content:
                                if not isinstance(c, dict) or c.get("type") != "tool_use":
                                    continue
                                name = c.get("name") or ""
                                tools[name] += 1
                                inp = c.get("input") or {}
                                if not isinstance(inp, dict):
                                    continue
                                if name == "Skill":
                                    sk = inp.get("skill")
                                    if sk:
                                        skills[sk] += 1
                                elif name == "Agent":
                                    sub = inp.get("subagent_type")
                                    if sub:
                                        agents[sub] += 1
                except OSError:
                    continue

    def rank(counter, total):
        items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return [
            {
                "name": k,
                "count": v,
                "share": round(v / total * 100, 1) if total else 0.0,
            }
            for k, v in items
        ]

    total_skills = sum(skills.values())
    total_agents = sum(agents.values())
    total_tools = sum(tools.values())

    out = {
        "days": days,
        "skills": rank(skills, total_skills),
        "agents": rank(agents, total_agents),
        "tools":  rank(tools, total_tools),
        "totals": {
            "skills": total_skills,
            "agents": total_agents,
            "tools":  total_tools,
        },
        "as_of": today.isoformat(),
    }

    try:
        os.makedirs(os.path.dirname(LEADERBOARD_CACHE), exist_ok=True)
        with open(LEADERBOARD_CACHE, "w") as f:
            json.dump(out, f)
    except Exception:
        pass
    return out


def compute_hourly(days=30):
    """Hour-of-day distribution over the last `days` days. 24 buckets.

    Tells you when in the day you're most active. Cached like heatmap.
    """
    try:
        if os.path.exists(HOURLY_CACHE):
            age = time.time() - os.path.getmtime(HOURLY_CACHE)
            if age < HEATMAP_TTL_SECONDS:
                with open(HOURLY_CACHE, "r") as f:
                    return json.load(f)
    except Exception:
        pass

    from datetime import timedelta
    today = datetime.now().astimezone()
    cutoff_dt = datetime.combine(
        (today - timedelta(days=days - 1)).date(),
        dtime.min, tzinfo=today.tzinfo,
    )
    cutoff_ts = cutoff_dt.timestamp()
    file_cutoff_ts = datetime.now().timestamp() - ((days + 2) * 86400)

    buckets = [0] * 24

    if os.path.isdir(PROJECTS_DIR):
        for project in os.listdir(PROJECTS_DIR):
            project_path = os.path.join(PROJECTS_DIR, project)
            if not os.path.isdir(project_path):
                continue
            for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
                try:
                    if os.path.getmtime(fp) < file_cutoff_ts:
                        continue
                except OSError:
                    continue
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
                            if rec.get("type") != "assistant":
                                continue
                            ts = rec.get("timestamp")
                            if not ts:
                                continue
                            try:
                                rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                rec_ts = rec_dt.timestamp()
                            except (ValueError, TypeError):
                                continue
                            if rec_ts < cutoff_ts:
                                continue
                            msg = rec.get("message") or {}
                            if not isinstance(msg, dict):
                                continue
                            usage = msg.get("usage") or {}
                            if not isinstance(usage, dict):
                                continue
                            total = (
                                int(usage.get("input_tokens", 0) or 0)
                                + int(usage.get("output_tokens", 0) or 0)
                                + int(usage.get("cache_creation_input_tokens", 0) or 0)
                            )
                            if not total:
                                continue
                            local_dt = rec_dt.astimezone()
                            buckets[local_dt.hour] += total
                except OSError:
                    continue

    out = {
        "days": days,
        "buckets": buckets,
        "max": max(buckets) if buckets else 0,
        "total": sum(buckets),
        "peak_hour": (buckets.index(max(buckets)) if any(buckets) else None),
        "as_of": today.isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(HOURLY_CACHE), exist_ok=True)
        with open(HOURLY_CACHE, "w") as f:
            json.dump(out, f)
    except Exception:
        pass
    return out


def _scan_seven_day_projects():
    """Walk last 7 days of jsonl files and aggregate tokens per project.

    Returns: list of {name, tokens, day_buckets} sorted by tokens desc, top 5.

    day_buckets is a 7-element list of token counts for [6 days ago ... today]
    so the widget can draw a sparkline-style bar inside the project row.
    """
    cutoff_dt = _days_ago_iso(7)
    cutoff_ts = cutoff_dt.timestamp()
    today_dt = datetime.now().astimezone()

    # File-level cutoff: anything modified in last 8 days might contain
    # entries we care about (extra day for timezone/clock drift slack)
    file_cutoff_ts = datetime.now().timestamp() - (8 * 24 * 3600)

    by_project = {}  # project -> {"tokens": int, "buckets": [0]*7}

    if not os.path.isdir(PROJECTS_DIR):
        return []

    for project in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, project)
        if not os.path.isdir(project_path):
            continue
        for fp in glob.glob(os.path.join(project_path, "*.jsonl")):
            try:
                if os.path.getmtime(fp) < file_cutoff_ts:
                    continue
            except OSError:
                continue
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
                        if rec.get("type") != "assistant":
                            continue
                        ts = rec.get("timestamp")
                        if not ts:
                            continue
                        try:
                            rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            rec_ts = rec_dt.timestamp()
                        except (ValueError, TypeError):
                            continue
                        if rec_ts < cutoff_ts:
                            continue

                        msg = rec.get("message") or {}
                        if not isinstance(msg, dict):
                            continue
                        usage = msg.get("usage") or {}
                        if not isinstance(usage, dict):
                            continue
                        total = (
                            int(usage.get("input_tokens", 0) or 0)
                            + int(usage.get("output_tokens", 0) or 0)
                            + int(usage.get("cache_creation_input_tokens", 0) or 0)
                        )
                        if not total:
                            continue

                        slot = by_project.setdefault(
                            project, {"tokens": 0, "buckets": [0] * 7}
                        )
                        slot["tokens"] += total

                        # Day index: 0 = 6 days ago, 6 = today (local time)
                        days_back = (today_dt.date() - rec_dt.astimezone().date()).days
                        idx = 6 - days_back
                        if 0 <= idx < 7:
                            slot["buckets"][idx] += total
            except OSError:
                continue

    # Top 5 projects by total tokens
    items = sorted(by_project.items(), key=lambda kv: kv[1]["tokens"], reverse=True)
    out = []
    for project_folder, slot in items[:5]:
        out.append({
            "name": _decode_project_path(project_folder),
            "tokens": slot["tokens"],
            "buckets": slot["buckets"],
        })
    return out


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
        # 7-day per-project breakdown for the drill-down view
        "projects_7d": _scan_seven_day_projects(),
        # 365-day token activity heatmap (cached, refreshed hourly)
        "heatmap": compute_heatmap(365),
        # Hour-of-day distribution over last 30 days (cached)
        "hourly": compute_hourly(30),
        # 30-day skills + agents + tools leaderboard (cached)
        "leaderboard": compute_leaderboard(30),
        # API-equivalent cost (month-to-date, projected, last-30d) (cached)
        "cost": compute_cost(30),
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
