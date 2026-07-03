#!/bin/bash
# ==========================================================
#  Big Grove Sales Portal — one-click deploy to GitHub Pages
#  Double-click this file to publish your latest changes.
# ==========================================================

PROJECT="/Users/troymyler/Documents/Claude/Projects/Big Grove Sales Portal"

cd "$PROJECT" || {
  echo "❌ Could not find the project folder:"
  echo "   $PROJECT"
  echo
  read -n1 -s -p "Press any key to close..."
  exit 1
}

echo "=============================================="
echo "   Big Grove Sales Portal — Deploy to GitHub"
echo "=============================================="
echo

# Ask for a short description of the update (optional)
read -r -p "Describe this update (or just press Enter): " MSG
if [ -z "$MSG" ]; then
  MSG="Update portal $(date '+%Y-%m-%d %H:%M')"
fi

echo
echo "→ Staging changes..."
git add -A

echo "→ Committing..."
git commit -m "$MSG" || echo "  (nothing new to commit — will still push)"

echo "→ Pushing to GitHub..."
echo "  (If asked for a password, paste your ghp_... token — it stays invisible.)"
echo
SITE="https://bgtroy2026.github.io/BigGroveSales/"

if git push; then
  echo
  echo "✅ Pushed. GitHub Pages usually publishes within a minute or two."
  echo "→ Opening the live site (may take a minute to show your changes)..."
  sleep 2
  open "$SITE"
else
  echo
  echo "⚠️  Push didn't complete."
  read -r -p "Retry with a fresh commit to re-trigger the deploy? [y/N] " R
  if [ "$R" = "y" ] || [ "$R" = "Y" ]; then
    git commit --allow-empty -m "Retrigger deploy $(date '+%Y-%m-%d %H:%M')"
    if git push; then echo "✅ Retry complete."; sleep 2; open "$SITE"; else echo "❌ Still failing — check githubstatus.com or ask for help."; fi
  fi
fi

echo
read -n1 -s -p "Press any key to close this window..."
echo
