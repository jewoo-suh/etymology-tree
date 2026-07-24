#!/usr/bin/env bash
# Reproducible build for the live GitHub Pages deploy (jewoo-suh.github.io/etymology-tree).
#
# The deployed load-once site is NOT built with the committed NODE_TARGET default
# (795k, which is tuned for the size-capped single-file bundle). It is built with an
# explicit --target so coverage matches what the live site ships. English is shipped
# WHOLE (FULL_LANGS in export_graph.py) because it is the primary search language;
# --target sizes the other 4,497 languages' sqrt quotas and the compound-leaf fill.
#
# Rebuilding without --target 2400000 silently shrinks the site and drops common
# words. Always deploy with this script.
set -e
cd "$(dirname "$0")/.."
TARGET=2400000

echo "== graph2 (core builder) =="       ; python build/graph2.py
echo "== export compact (bundle) =="      ; python build/export_graph.py
echo "== export web (deployed source) ==" ; python build/export_graph.py --glossall --target "$TARGET"
echo "== export full (offline) =="        ; python build/export_graph.py --full
echo "== package site =="                 ; python build/site.py
echo "== QA web =="   ; node --max-old-space-size=6000 tools/qa.js web/graph-web.json
echo "== QA full =="  ; node --max-old-space-size=6000 tools/qa.js web/graph-full.json
echo "== sanity =="   ; node --max-old-space-size=6000 tools/sanity.js | head -12
echo "== sitecheck ==" ; node tools/sitecheck.js
echo "DONE -- commit the new graph-core/gloss gz + index.html and push to master."
