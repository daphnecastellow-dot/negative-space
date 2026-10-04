#!/usr/bin/env python3
"""Preserve failed hypotheses, missing evidence, and research dead ends.

A not-found result is recorded as a search outcome, never as proof of absence.
"""

from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

FORMAT = "negative-space/0.1"
HYPOTHESIS_STATUSES = ("open", "weakened", "parked", "rejected")
CHECK_OUTCOMES = ("found", "not-found", "inconclusive", "unavailable", "contradictory")

class NegativeSpaceError(Exception):
    pass

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def new_project(title: str) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise NegativeSpaceError("title cannot be empty")
    return {"format": FORMAT, "title": title, "created_at": now_utc(), "hypotheses": [], "checks": []}

def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
    high = 0
    for item in items:
        value = item.get("id", "")
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            high = max(high, int(value[len(prefix):]))
    return f"{prefix}{high + 1:03d}"

def _valid_url_or_blank(value: str) -> bool:
    return not value or bool(re.match(r"^https?://", value))

def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise NegativeSpaceError("unsupported project format")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise NegativeSpaceError("project requires a title")
    for key in ("hypotheses", "checks"):
        if not isinstance(data.get(key), list):
            raise NegativeSpaceError(f"project requires a {key} list")
    hids = set()
    for h in data["hypotheses"]:
        hid = h.get("id")
        if not isinstance(hid, str) or not hid or hid in hids:
            raise NegativeSpaceError("invalid or duplicate hypothesis id")
        hids.add(hid)
        if not isinstance(h.get("text"), str) or not h["text"].strip():
            raise NegativeSpaceError(f"{hid}: hypothesis text cannot be empty")
        if h.get("status") not in HYPOTHESIS_STATUSES:
            raise NegativeSpaceError(f"{hid}: invalid hypothesis status")
        if not isinstance(h.get("history"), list) or not h["history"]:
            raise NegativeSpaceError(f"{hid}: hypothesis requires history")
    cids = set()
    for c in data["checks"]:
        cid = c.get("id")
        if not isinstance(cid, str) or not cid or cid in cids:
            raise NegativeSpaceError("invalid or duplicate check id")
        cids.add(cid)
        if c.get("hypothesis") and c["hypothesis"] not in hids:
            raise NegativeSpaceError(f"{cid}: unknown hypothesis")
        if c.get("outcome") not in CHECK_OUTCOMES:
            raise NegativeSpaceError(f"{cid}: invalid check outcome")
        for field in ("target", "method", "result"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                raise NegativeSpaceError(f"{cid}: {field} cannot be empty")
        if not _valid_url_or_blank(c.get("url", "")):
            raise NegativeSpaceError(f"{cid}: url must begin with http:// or https://")

def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise NegativeSpaceError(f"project not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NegativeSpaceError(f"invalid JSON in {p}: {exc}") from exc
    validate(data)
    return data

def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def find_hypothesis(data: dict[str, Any], hid: str) -> dict[str, Any]:
    for h in data["hypotheses"]:
        if h["id"] == hid:
            return h
    raise NegativeSpaceError(f"hypothesis not found: {hid}")

def add_hypothesis(data: dict[str, Any], text: str, note: str | None = None, reopen_when: str | None = None) -> str:
    text = text.strip()
    if not text:
        raise NegativeSpaceError("hypothesis text cannot be empty")
    hid = _next_id(data["hypotheses"], "H")
    data["hypotheses"].append({
        "id": hid, "text": text, "status": "open", "note": note or "", "reopen_when": reopen_when or "",
        "history": [{"at": now_utc(), "action": "created", "status": "open", "reason": note or ""}],
    })
    return hid

def add_check(data: dict[str, Any], hypothesis: str | None, target: str, method: str, expected: str | None,
              outcome: str, result: str, source: str | None = None, url: str | None = None, note: str | None = None) -> str:
    if hypothesis:
        find_hypothesis(data, hypothesis)
    if outcome not in CHECK_OUTCOMES:
        raise NegativeSpaceError(f"invalid check outcome: {outcome}")
    for label, value in (("target", target), ("method", method), ("result", result)):
        if not value.strip():
            raise NegativeSpaceError(f"{label} cannot be empty")
    if url and not _valid_url_or_blank(url):
        raise NegativeSpaceError("url must begin with http:// or https://")
    cid = _next_id(data["checks"], "K")
    data["checks"].append({
        "id": cid, "hypothesis": hypothesis or "", "target": target.strip(), "method": method.strip(),
        "expected": (expected or "").strip(), "outcome": outcome, "result": result.strip(),
        "source": (source or "").strip(), "url": url or "", "note": note or "", "checked_at": now_utc(),
    })
    return cid

def change_status(data: dict[str, Any], hid: str, status: str, reason: str, reopen_when: str | None = None) -> None:
    h = find_hypothesis(data, hid)
    if status not in HYPOTHESIS_STATUSES:
        raise NegativeSpaceError(f"invalid hypothesis status: {status}")
    if not reason.strip():
        raise NegativeSpaceError("status change requires a reason")
    old = h["status"]
    h["status"] = status
    if reopen_when is not None:
        h["reopen_when"] = reopen_when.strip()
    h["history"].append({
        "at": now_utc(), "action": "status", "previous_status": old, "status": status,
        "reason": reason.strip(), "reopen_when": h.get("reopen_when", ""),
    })

def hypothesis_checks(data: dict[str, Any], hid: str) -> list[dict[str, Any]]:
    find_hypothesis(data, hid)
    return [c for c in data["checks"] if c.get("hypothesis") == hid]

def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['title']}", "", f"_Negative Space format: `{FORMAT}`_", "",
        "> `not-found` means the recorded check did not find the expected material. It does not prove the material never existed.",
        "", "## Hypotheses", "",
    ]
    if not data["hypotheses"]:
        lines += ["_No hypotheses yet._", ""]
    for h in data["hypotheses"]:
        lines += [f"### {h['id']} · {h['status']}", "", h["text"], ""]
        if h.get("note"):
            lines += [f"**Note:** {h['note']}", ""]
        if h.get("reopen_when"):
            lines += [f"**Reopen when:** {h['reopen_when']}", ""]
        checks = hypothesis_checks(data, h["id"])
        if checks:
            lines += ["**Checks:**", ""]
            for c in checks:
                lines.append(f"- {c['id']} · **{c['outcome']}** · {c['target']}")
            lines.append("")
        lines += ["**Status history:**", ""]
        for event in h["history"]:
            item = f"- {event['at']} · **{event['status']}** · {event['action']}"
            if event.get("reason"):
                item += f" · {event['reason']}"
            lines.append(item)
        lines.append("")
    lines += ["## Checks", ""]
    if not data["checks"]:
        lines += ["_No checks yet._", ""]
    for c in data["checks"]:
        lines += [f"### {c['id']} · {c['outcome']}", ""]
        if c.get("hypothesis"):
            lines += [f"**Hypothesis:** {c['hypothesis']}", ""]
        lines += [f"**Target:** {c['target']}", "", f"**Method:** {c['method']}", ""]
        if c.get("expected"):
            lines += [f"**Expected evidence:** {c['expected']}", ""]
        lines += [f"**Recorded result:** {c['result']}", ""]
        if c.get("source"):
            source = c["source"] + (f" · {c['url']}" if c.get("url") else "")
            lines += [f"**Source:** {source}", ""]
        if c.get("note"):
            lines += [f"**Note:** {c['note']}", ""]
    return "\n".join(lines).rstrip() + "\n"

def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for h in data["hypotheses"]:
        label = h["text"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {h["id"]}["{h["id"]} · {h["status"]} · {label}"]')
    for c in data["checks"]:
        label = c["target"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {c["id"]}["{c["id"]} · {c["outcome"]} · {label}"]')
        if c.get("hypothesis"):
            lines.append(f'  {c["hypothesis"]} -->|checked by| {c["id"]}')
    return "\n".join(lines) + "\n"

def dead_ends(data: dict[str, Any]) -> str:
    lines = ["# Dead ends and parked paths", ""]
    hs = [h for h in data["hypotheses"] if h["status"] in ("parked", "rejected")]
    if not hs:
        lines += ["_No parked or rejected hypotheses._", ""]
    for h in hs:
        lines += [f"## {h['id']} · {h['status']}", "", h["text"], ""]
        if h.get("reopen_when"):
            lines += [f"**Reopen when:** {h['reopen_when']}", ""]
        for c in hypothesis_checks(data, h["id"]):
            lines.append(f"- {c['id']} · **{c['outcome']}** · {c['result']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def summary(data: dict[str, Any]) -> str:
    counts = {status: sum(h["status"] == status for h in data["hypotheses"]) for status in HYPOTHESIS_STATUSES}
    nf = sum(c["outcome"] == "not-found" for c in data["checks"])
    return (f"{data['title']}: {len(data['hypotheses'])} hypothesis(es), {len(data['checks'])} check(s), "
            f"{nf} not-found result(s), {counts['parked']} parked, {counts['rejected']} rejected")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="negative-space", description="Preserve failed hypotheses, missing evidence, and research dead ends.")
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("new"); q.add_argument("file"); q.add_argument("--title", required=True)
    q = sub.add_parser("hypothesis"); q.add_argument("file"); q.add_argument("text"); q.add_argument("--note"); q.add_argument("--reopen-when")
    q = sub.add_parser("check"); q.add_argument("file"); q.add_argument("--hypothesis"); q.add_argument("--target", required=True); q.add_argument("--method", required=True); q.add_argument("--expected"); q.add_argument("--outcome", choices=CHECK_OUTCOMES, required=True); q.add_argument("--result", required=True); q.add_argument("--source"); q.add_argument("--url"); q.add_argument("--note")
    q = sub.add_parser("status"); q.add_argument("file"); q.add_argument("hypothesis_id"); q.add_argument("status", choices=HYPOTHESIS_STATUSES); q.add_argument("--reason", required=True); q.add_argument("--reopen-when")
    for name in ("show", "validate"):
        q = sub.add_parser(name); q.add_argument("file")
    for name in ("render", "dead-ends", "mermaid"):
        q = sub.add_parser(name); q.add_argument("file"); q.add_argument("-o", "--output")
    return p

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "new":
            if Path(args.file).exists():
                raise NegativeSpaceError(f"refusing to overwrite existing file: {args.file}")
            save(args.file, new_project(args.title)); print(f"created {args.file}"); return 0
        data = load(args.file)
        if args.command == "hypothesis":
            hid = add_hypothesis(data, args.text, args.note, args.reopen_when); save(args.file, data); print(hid)
        elif args.command == "check":
            cid = add_check(data, args.hypothesis, args.target, args.method, args.expected, args.outcome, args.result, args.source, args.url, args.note); save(args.file, data); print(cid)
        elif args.command == "status":
            change_status(data, args.hypothesis_id, args.status, args.reason, args.reopen_when); save(args.file, data); print(args.hypothesis_id)
        elif args.command == "show": print(summary(data))
        elif args.command == "validate": print(f"ok: {args.file}")
        else:
            output = {"render": render_markdown, "dead-ends": dead_ends, "mermaid": render_mermaid}[args.command](data)
            if args.output: Path(args.output).write_text(output, encoding="utf-8"); print(args.output)
            else: print(output, end="")
        return 0
    except NegativeSpaceError as exc:
        print(f"negative-space: {exc}", file=sys.stderr); return 2

if __name__ == "__main__":
    raise SystemExit(main())
