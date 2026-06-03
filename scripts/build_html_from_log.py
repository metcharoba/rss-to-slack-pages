#!/usr/bin/env python3

import html
import json
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_FILE = BASE_DIR / "logs" / "rss_to_slack_log.jsonl"
OUTPUT_DIR = BASE_DIR / "public"
OUTPUT_FILE = OUTPUT_DIR / "index.html"


def load_items() -> list[dict[str, str]]:
    if not LOG_FILE.exists():
        return []

    items = []
    for line_number, raw_line in enumerate(LOG_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse {LOG_FILE} line {line_number}: {exc}") from exc

        items.append(
            {
                "sent_at": str(data.get("sent_at", "")),
                "title": str(data.get("title", "")),
                "feed_url": str(data.get("feed_url", "")),
                "link": str(data.get("link", "")),
            }
        )

    return sorted(items, key=lambda item: item["sent_at"], reverse=True)


def page_html(items: list[dict[str, str]]) -> str:
    rows = "\n".join(render_item(item) for item in items)
    if not rows:
        rows = '<p class="empty">No sent RSS items logged yet.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CreativeVault RSS Log</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #1f2933;
      background: #f7f8fa;
    }}
    body {{
      margin: 0;
      padding: 32px 20px;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 20px;
      font-size: 28px;
      font-weight: 700;
    }}
    .item {{
      margin: 0 0 12px;
      padding: 16px;
      border: 1px solid #d7dce2;
      border-radius: 8px;
      background: #ffffff;
    }}
    .meta {{
      margin: 0 0 8px;
      color: #65717f;
      font-size: 13px;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 18px;
      line-height: 1.35;
    }}
    a {{
      color: #0f62fe;
      overflow-wrap: anywhere;
    }}
    dl {{
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 6px 10px;
      margin: 0;
      font-size: 14px;
    }}
    dt {{
      color: #65717f;
      font-weight: 600;
    }}
    dd {{
      margin: 0;
      min-width: 0;
      overflow-wrap: anywhere;
    }}
    .empty {{
      padding: 16px;
      border: 1px solid #d7dce2;
      border-radius: 8px;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <main>
    <h1>CreativeVault RSS Log</h1>
    {rows}
  </main>
</body>
</html>
"""


def render_item(item: dict[str, str]) -> str:
    sent_at = html.escape(item["sent_at"])
    feed_url_html = render_url_value(item["feed_url"])
    link_html = render_url_value(item["link"])
    title_html = render_title_link(item["title"], item["link"])

    return f"""<article class="item">
      <p class="meta">{sent_at}</p>
      <h2>{title_html}</h2>
      <dl>
        <dt>feed</dt>
        <dd>{feed_url_html}</dd>
        <dt>link</dt>
        <dd>{link_html}</dd>
      </dl>
    </article>"""


def is_http_url(value: str) -> bool:
    parsed_url = urlparse(value)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def render_url_value(value: str) -> str:
    escaped_value = html.escape(value)
    if not is_http_url(value):
        return escaped_value
    return f'<a href="{escaped_value}">{escaped_value}</a>'


def render_title_link(title: str, link: str) -> str:
    escaped_title = html.escape(title)
    if not is_http_url(link):
        return escaped_title
    return f'<a href="{html.escape(link)}">{escaped_title}</a>'


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(page_html(load_items()), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
