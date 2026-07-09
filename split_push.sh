#!/usr/bin/env bash
set -euo pipefail

REMOTE=origin
BRANCH=$(git rev-parse --abbrev-ref HEAD)   # e.g. master

# ---- Step 1: undo the last commit, KEEP all files on disk ----
# Guard: if we've already started splitting, don't reset again (makes reruns safe)
if git log --oneline -n 20 | grep -q "data: add "; then
    echo "Split already in progress — skipping the reset."
elif git rev-parse --verify --quiet HEAD~1 >/dev/null; then
    echo "Undoing last commit (earlier history kept, files preserved)..."
    git reset --mixed HEAD~1
else
    echo "Last commit was the initial commit — removing it (files preserved)..."
    git update-ref -d HEAD
    git reset -q
fi

# ---- Step 2: one commit + push per leaf data subfolder ----
for dir in trial_*/data/*/; do
    dir=${dir%/}
    [ -d "$dir" ] || continue
    git add -- "$dir"
    if git diff --cached --quiet; then
        echo "  $dir already committed — skipping"
        continue
    fi
    echo ">>> Committing $dir"
    git commit -q -m "data: add $dir"
    echo ">>> Pushing $dir ..."
    git push -q -u "$REMOTE" "$BRANCH"
    echo "    done."
done

# ---- Step 3: commit + push the source and everything else ----
git add -A
if git diff --cached --quiet; then
    echo "Nothing left to commit."
else
    echo ">>> Committing source + results"
    git commit -q -m "src: add source code and results"
    git push -q "$REMOTE" "$BRANCH"
fi

echo "All done — remote is up to date."
