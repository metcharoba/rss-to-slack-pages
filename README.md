# RSS to Slack Minimal Test

## Purpose

This is a small CreativeVault experiment for fetching public RSS or Atom feeds and sending unsent latest entries to Slack.

Use only public RSS feeds and public-safe messages. Do not include patient information, internal clinic information, unpublished research, MedicalVault content, credentials, API keys, or real webhook URLs in this directory.

## Required Environment Variables

- `RSS_URL`: Public RSS or Atom feed URL to fetch.
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL used by the test script.
- `MAX_ITEMS_PER_RUN`: Optional positive integer. Limits how many new items are sent in one run.
- `DRY_RUN`: Optional. Set to `1` to print planned Slack messages without sending or updating state/log files.

Set `SLACK_WEBHOOK_URL` in the terminal session before running the script. `RSS_URL` is optional; when it is set, the script uses only that one feed. When `RSS_URL` is not set, the script reads `feeds.txt`.

Do not save real webhook URLs, secrets, tokens, or credentials in files.

## Local Environment File

For launchd, use `.env.local` so `SLACK_WEBHOOK_URL` does not need to be written into the plist.

Create it from the example file:

```sh
cp .env.example .env.local
chmod 600 .env.local
```

Then edit `.env.local` and replace the dummy `SLACK_WEBHOOK_URL` with the real Slack Incoming Webhook URL. Keep `DRY_RUN=1` while testing. Remove `DRY_RUN=1` or set it to another value only when ready to send.

Do not commit, paste, or share `.env.local`.

`.env.local` contains the real Slack webhook URL, so do not publish or share it.

## Feed List

Put public RSS or Atom feed URLs in `feeds.txt`, one URL per line.

```txt
https://www.nasa.gov/news-release/feed/
```

Blank lines and lines starting with `#` are ignored.

## State and Logs

- `state/sent_items.json`: created at runtime to remember sent article URLs.
- `logs/rss_to_slack_log.jsonl`: created at runtime to record newly sent items.

If an article link is already in `state/sent_items.json`, the script skips it and does not send it again.

## Run

From this directory:

```sh
export SLACK_WEBHOOK_URL="ここを実際のSlack Incoming Webhook URLに置き換える"
python3 scripts/fetch_rss_to_slack.py
```

Use one feed directly with `RSS_URL`:

```sh
export RSS_URL="https://www.nasa.gov/news-release/feed/"
export SLACK_WEBHOOK_URL="ここを実際のSlack Incoming Webhook URLに置き換える"
python3 scripts/fetch_rss_to_slack.py
```

Limit the number of new items sent:

```sh
export MAX_ITEMS_PER_RUN=1
export SLACK_WEBHOOK_URL="ここを実際のSlack Incoming Webhook URLに置き換える"
python3 scripts/fetch_rss_to_slack.py
```

Preview without sending to Slack or updating `state/` and `logs/`:

```sh
export DRY_RUN=1
export MAX_ITEMS_PER_RUN=1
python3 scripts/fetch_rss_to_slack.py
```

Run through the wrapper script:

```sh
scripts/run_rss_to_slack.sh
```

## launchd Example

`launchd/com.koji.creativevault.rss-to-slack.example.plist` is an example plist for running this script once per day at 9:00. It points to `scripts/run_rss_to_slack.sh`, which loads `.env.local` when that file exists.

Before registering it with `launchd`, confirm these points manually:

- The example plist does not contain `SLACK_WEBHOOK_URL`.
- `.env.local` exists, has file mode `600`, and is not shared.
- The wrapper works from Terminal with `DRY_RUN=1`.
- The wrapper works from Terminal with `MAX_ITEMS_PER_RUN=1` before launchd registration.
- `feeds.txt` contains only public RSS or Atom feeds.
- `state/` and `logs/` can be created or written by the user account that will run the job.

Manual dry-run check:

```sh
cd /Users/metcharoba/CreativeVault/20_rss_to_slack_test
unset RSS_URL
scripts/run_rss_to_slack.sh
```

Manual real-send check before launchd registration:

```sh
cd /Users/metcharoba/CreativeVault/20_rss_to_slack_test
scripts/run_rss_to_slack.sh
```

Do not register the plist until the manual checks behave as expected.

After launchd runs, check the scheduled-run logs:

```sh
cd /Users/metcharoba/CreativeVault/20_rss_to_slack_test
tail -n 40 logs/launchd_stdout.log
tail -n 40 logs/launchd_stderr.log
tail -n 20 logs/rss_to_slack_log.jsonl
```

These logs should show normal run messages and public RSS item metadata only. Do not paste or publish logs if they contain unexpected private data.

## Build Local HTML

Generate a small local HTML page from `logs/rss_to_slack_log.jsonl`:

```sh
cd /Users/metcharoba/CreativeVault/20_rss_to_slack_test
python3 scripts/build_html_from_log.py
```

The output is `public/index.html`. It includes only `sent_at`, `title`, `feed_url`, and `link` from the JSONL log.

## GitHub Pages Preflight

Before enabling GitHub Pages or pushing this workflow:

- Confirm `public/index.html` exists and contains only public RSS item metadata.
- Confirm `.env.local`, `logs/`, and `state/` are not committed or published.
- Confirm the repository Pages source is set to `main` branch / `/docs` folder.
- Confirm no webhook URLs, API keys, tokens, credentials, private notes, patient information, clinic information, or unpublished research are present in published files.

## Notes

- `RSS_URL` and `SLACK_WEBHOOK_URL` are read only from environment variables.
- If `RSS_URL` is not set, feed URLs are read from `feeds.txt`.
- The Slack message includes `title`, `link`, and a CreativeVault note.
- The script checks only the latest item from each feed.
- `DRY_RUN=1` does not require `SLACK_WEBHOOK_URL`.
- If RSS parsing fails, the script prints the RSS HTTP status, Content-Type, and first 100 body characters to stderr.
- Do not use private feeds, confidential workspaces, patient information, clinic information, or unpublished research.
- Do not commit or save webhook URLs, API keys, tokens, or credentials.

## GitHub Pages

Public page:

https://metcharoba.github.io/rss-to-slack-pages/

This project uses the GitHub Pages `main` branch / `/docs` folder publishing method.

Publishing source:

- Branch: `main`
- Folder: `/docs`

HTML update / GitHub Pages operation:

- Run `./scripts/update_pages_html.sh` to regenerate `public/index.html` and copy it to `docs/index.html`.
- `docs/index.html` is the published GitHub Pages file.
- Do not use a GitHub Actions workflow for this version.
- When staging updates, use explicit file paths such as `git add docs/index.html public/index.html README.md`, not `git add .`.

Notes:

- `.env.local` is not committed.
- `logs/` and `state/` are not committed.
- GitHub Actions workflow is not used for this version.
