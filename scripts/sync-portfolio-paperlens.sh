#!/usr/bin/env bash
# Build public PaperLens for portfolio (Netlify) and copy into Gatsby static/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORTFOLIO="${PORTFOLIO_ROOT:-$HOME/myblogs/projects}"

if [[ ! -d "$PORTFOLIO" ]]; then
  echo "Portfolio not found at $PORTFOLIO — set PORTFOLIO_ROOT" >&2
  exit 1
fi

echo "Building PaperLens for /paperlens/ …"
cd "$ROOT/frontend"
npm run build:portfolio

DEST="$PORTFOLIO/static/paperlens"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -r dist/* "$DEST/"
cp "$ROOT/serving/portfolio/config.js" "$DEST/config.js"

echo "Copied to $DEST"
echo "Next: commit & push portfolio repo, redeploy Netlify + Railway API with CORS_ORIGINS"
