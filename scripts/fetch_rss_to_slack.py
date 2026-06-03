#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

FEEDS_FILE = Path("feeds.txt")
STATE_DIR = Path("state")
LOGS_DIR = Path("logs")
SENT_ITEMS_FILE = STATE_DIR / "sent_items.json"
LOG_FILE = LOGS_DIR / "rss_to_slack_log.jsonl"
CREATIVEVAULT_NOTE = "CreativeVault note: public RSS collection test."


class FetchResult(NamedTuple):
    status: int
    content_type: str
    body: str


def require_url_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"{name} is not set.", file=sys.stderr)
        raise SystemExit(1)

    parsed_url = urllib.parse.urlparse(value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print(f"{name} must be a valid http or https URL.", file=sys.stderr)
        raise SystemExit(1)

    return value


def validate_url(name: str, value: str) -> str:
    parsed_url = urllib.parse.urlparse(value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print(f"{name} must be a valid http or https URL.", file=sys.stderr)
        raise SystemExit(1)
    return value


def load_max_items_per_run() -> Optional[int]:
    value = os.environ.get("MAX_ITEMS_PER_RUN")
    if not value:
        return None

    try:
        max_items = int(value)
    except ValueError:
        print("MAX_ITEMS_PER_RUN must be a positive integer.", file=sys.stderr)
        raise SystemExit(1)

    if max_items <= 0:
        print("MAX_ITEMS_PER_RUN must be a positive integer.", file=sys.stderr)
        raise SystemExit(1)

    return max_items


def is_dry_run() -> bool:
    return os.environ.get("DRY_RUN") == "1"


def load_feed_urls() -> Tuple[str, ...]:
    rss_url = os.environ.get("RSS_URL")
    if rss_url:
        return (validate_url("RSS_URL", rss_url),)

    if not FEEDS_FILE.exists():
        print("RSS_URL is not set and feeds.txt was not found.", file=sys.stderr)
        raise SystemExit(1)

    feed_urls = []
    for line_number, raw_line in enumerate(FEEDS_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        feed_urls.append(validate_url(f"feeds.txt line {line_number}", line))

    if not feed_urls:
        print("RSS_URL is not set and feeds.txt has no feed URLs.", file=sys.stderr)
        raise SystemExit(1)

    return tuple(feed_urls)


def ensure_output_dirs() -> None:
    STATE_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def load_sent_links() -> set:
    ensure_output_dirs()
    if not SENT_ITEMS_FILE.exists():
        return set()

    try:
        data = json.loads(SENT_ITEMS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse {SENT_ITEMS_FILE}: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if isinstance(data, dict) and isinstance(data.get("sent_links"), list):
        return {str(link) for link in data["sent_links"]}

    print(f"{SENT_ITEMS_FILE} must contain a JSON object with sent_links list.", file=sys.stderr)
    raise SystemExit(1)


def save_sent_links(sent_links: set) -> None:
    ensure_output_dirs()
    payload = {
        "sent_links": sorted(sent_links),
    }
    SENT_ITEMS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(feed_url: str, title: str, link: str) -> None:
    ensure_output_dirs()
    payload = {
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "feed_url": feed_url,
        "title": title,
        "link": link,
    }
    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def body_preview(body: str) -> str:
    return body[:100].replace("\n", "\\n").replace("\r", "\\r")


def print_rss_debug(result: FetchResult) -> None:
    print(f"RSS HTTP status: {result.status}", file=sys.stderr)
    print(f"RSS Content-Type: {result.content_type or '(none)'}", file=sys.stderr)
    print(f"RSS body first 100 chars: {body_preview(result.body)!r}", file=sys.stderr)


def fetch_text(url: str) -> FetchResult:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CreativeVault-RssToSlack-Test/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            return FetchResult(
                status=response.status,
                content_type=response.headers.get("Content-Type", ""),
                body=body,
            )
    except urllib.error.HTTPError as exc:
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        print(f"RSS fetch failed with HTTP {exc.code}.", file=sys.stderr)
        print(f"RSS Content-Type: {content_type or '(none)'}", file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(f"RSS fetch failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1)


def text_or_empty(element: Optional[ET.Element]) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def find_latest_entry(fetch_result: FetchResult) -> Tuple[str, str]:
    try:
        root = ET.fromstring(fetch_result.body)
    except ET.ParseError as exc:
        print(f"RSS parse failed: {exc}", file=sys.stderr)
        print_rss_debug(fetch_result)
        raise SystemExit(1)

    item = root.find("./channel/item")
    if item is not None:
        title = text_or_empty(item.find("title"))
        link = text_or_empty(item.find("link"))
        if title and link:
            return title, link

    namespaces = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", namespaces)
    if entry is not None:
        title = text_or_empty(entry.find("atom:title", namespaces))
        link_element = entry.find("atom:link[@href]", namespaces)
        link = link_element.attrib["href"].strip() if link_element is not None else ""
        if title and link:
            return title, link

    print("RSS parse failed: no latest item with title and link was found.", file=sys.stderr)
    print_rss_debug(fetch_result)
    raise SystemExit(1)


def post_to_slack(webhook_url: str, title: str, link: str) -> None:
    payload = {
        "text": f"title: {title}\nlink: {link}\n{CREATIVEVAULT_NOTE}",
    }
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CreativeVault-RssToSlack-Test/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            if 200 <= response.status < 300 and body.strip() == "ok":
                print("Latest RSS item sent to Slack.")
                return
            print(f"Slack returned HTTP {response.status}: {body}", file=sys.stderr)
            raise SystemExit(1)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Slack returned HTTP {exc.code}: {body}", file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(f"Slack request failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1)


def print_dry_run_item(feed_url: str, title: str, link: str) -> None:
    print("DRY_RUN=1: would send Slack message")
    print(f"feed: {feed_url}")
    print(f"title: {title}")
    print(f"link: {link}")
    print(CREATIVEVAULT_NOTE)


def main() -> int:
    dry_run = is_dry_run()
    webhook_url = "" if dry_run else require_url_env("SLACK_WEBHOOK_URL")
    max_items_per_run = load_max_items_per_run()
    feed_urls = load_feed_urls()
    sent_links = load_sent_links()
    sent_count = 0

    for feed_url in feed_urls:
        if max_items_per_run is not None and sent_count >= max_items_per_run:
            print(f"MAX_ITEMS_PER_RUN reached: {max_items_per_run}")
            break

        title, link = find_latest_entry(fetch_text(feed_url))
        if link in sent_links:
            print(f"Already sent, skipping: {link}")
            continue

        if dry_run:
            print_dry_run_item(feed_url, title, link)
            sent_count += 1
            continue

        post_to_slack(webhook_url, title, link)
        sent_links.add(link)
        save_sent_links(sent_links)
        append_log(feed_url, title, link)
        sent_count += 1

    print(f"Done. New items sent: {sent_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
