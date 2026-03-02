#!/bin/bash
# Auto-commit and push index.html on save
cd "$(dirname "$0")"

echo "Watching index.html — save the file and it auto-deploys to linardsb.github.io"
echo "Press Ctrl+C to stop"

fswatch -o index.html | while read; do
  sleep 1  # debounce rapid saves
  git add index.html
  git commit -m "update landing page" --quiet
  git push --quiet
  echo "$(date '+%H:%M:%S') — deployed to linardsb.github.io"
done
