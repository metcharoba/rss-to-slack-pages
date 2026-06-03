#!/bin/sh
set -eu

cd /Users/metcharoba/CreativeVault/20_rss_to_slack_test

if [ -f .env.local ]; then
  set -a
  . ./.env.local
  set +a
fi

exec /usr/bin/python3 scripts/fetch_rss_to_slack.py
