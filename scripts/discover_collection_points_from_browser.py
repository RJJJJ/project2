from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_URL = "https://api03.consumer.gov.mo/app/supermarket/main?me=&r=400&st=2&lang=cn&ctntype=2&ctnn=&plt=web"
DEFAULT_OUTPUT = Path("data/discovery/collection_points_capture.jsonl")
REQUEST_MARKER = "/itemsPrice/by_condition"


def parse_by_condition_url(raw_url: str, captured_at: str | None = None, source_url: str | None = None) -> dict[str, Any] | None:
    if REQUEST_MARKER not in raw_url:
        return None
    parsed = urlparse(raw_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    cet_values = query.get("cet") or []
    if not cet_values or "," not in cet_values[0]:
        return None
    lat_text, lng_text = cet_values[0].split(",", 1)
    try:
        lat = float(lat_text)
        lng = float(lng_text)
    except ValueError:
        return None
    dst_raw = (query.get("dst") or [None])[0]
    try:
        dst: int | None = int(float(dst_raw)) if dst_raw not in (None, "") else None
    except ValueError:
        dst = None
    row = {
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "source_url": source_url or "",
        "lat": lat,
        "lng": lng,
        "dst": dst,
        "categories": (query.get("categories") or [""])[0],
        "lang": (query.get("lang") or [""])[0],
        "key": (query.get("key") or [""])[0],
        "size": (query.get("size") or [""])[0],
        "items": (query.get("items") or [""])[0],
        "raw_url": raw_url,
    }
    row["dedupe_key"] = make_dedupe_key(row)
    return row


def make_dedupe_key(row: dict[str, Any]) -> str:
    return f"{row.get('lat')},{row.get('lng')},{row.get('dst')}"


def dedupe_capture_rows(rows: list[dict[str, Any]], mark_duplicates: bool = False) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = row.get("dedupe_key") or make_dedupe_key(row)
        copied = dict(row)
        copied["dedupe_key"] = key
        duplicate = key in seen
        if mark_duplicates:
            copied["duplicate"] = duplicate
            output.append(copied)
        elif not duplicate:
            output.append(copied)
        seen.add(key)
    return output


def load_existing_dedupe_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys.add(str(row.get("dedupe_key") or make_dedupe_key(row)))
    return keys


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_browser_capture(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {"ok": False, "captured": 0, "errors": ["Playwright is not installed. Install it manually before using browser capture."], "detail": str(exc)}

    output = Path(args.output)
    seen = load_existing_dedupe_keys(output) if args.dedupe else set()
    captured = 0
    duplicates = 0
    stopped = False

    def handle_sigint(signum, frame):  # noqa: ARG001
        nonlocal stopped
        stopped = True
        print("\nStopping capture after current browser loop...", flush=True)

    signal.signal(signal.SIGINT, handle_sigint)
    deadline = time.time() + args.timeout_seconds

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_page()

        def on_request(request):
            nonlocal captured, duplicates
            row = parse_by_condition_url(request.url, source_url=args.url)
            if not row:
                return
            key = str(row["dedupe_key"])
            duplicate = args.dedupe and key in seen
            row["duplicate"] = duplicate
            if duplicate:
                duplicates += 1
                print(f"duplicate capture ignored: {key}", flush=True)
                return
            seen.add(key)
            append_jsonl(output, row)
            captured += 1
            print(f"captured #{captured}: lat={row['lat']} lng={row['lng']} dst={row['dst']}", flush=True)

        page.on("request", on_request)
        page.goto(args.url, wait_until="domcontentloaded")
        print("Browser opened. Manually click 查看更多 -> select district -> 確定修改.", flush=True)
        while not stopped and captured < args.max_captures and time.time() < deadline:
            page.wait_for_timeout(1000)
        browser.close()

    return {"ok": True, "captured": captured, "duplicates": duplicates, "output": str(output), "max_captures": args.max_captures}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Consumer Council collection point cet/dst requests from a browser.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--lang", default="cn")
    parser.add_argument("--manual", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--headful", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-captures", type=int, default=60)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--dedupe", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    summary = run_browser_capture(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
