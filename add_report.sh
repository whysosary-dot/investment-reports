#!/bin/bash
# Investment Reports — Auto Add & Push
# Usage:
#   ./add_report.sh add <id> <date> <title> <summary> <tags-csv> <pc-file> [ipad-file]
#   ./add_report.sh push                                 # commit & push pending changes
#   ./add_report.sh remove <id>                          # remove a report
#
# Example:
#   ./add_report.sh add "20260429-sangshin-vs-shinheung" "2026-04-29" \
#     "상신이디피 vs 신흥에스이씨 비교분석" \
#     "사업보고서 6개년 매출·캐파·가동률 비교, ESS/EV/각통/원통 시나리오 분석" \
#     "KR,Sector,2차전지" \
#     "/path/to/PC.html" "/path/to/iPad.html"

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INDEX="$REPO_DIR/index.html"
REPORTS_DIR="$REPO_DIR/reports"

cmd="${1:-help}"

case "$cmd" in
  add)
    ID="$2"; DATE="$3"; TITLE="$4"; SUMMARY="$5"; TAGS="$6"; PC_SRC="$7"; IPAD_SRC="${8:-}"
    if [ -z "$ID" ] || [ -z "$DATE" ] || [ -z "$TITLE" ] || [ -z "$PC_SRC" ]; then
      echo "Usage: $0 add <id> <date> <title> <summary> <tags-csv> <pc-file> [ipad-file]"
      exit 1
    fi
    mkdir -p "$REPORTS_DIR"

    PC_NAME=$(basename "$PC_SRC")
    cp "$PC_SRC" "$REPORTS_DIR/$PC_NAME"
    PC_PATH="reports/$PC_NAME"

    IPAD_PATH=""
    if [ -n "$IPAD_SRC" ] && [ -f "$IPAD_SRC" ]; then
      IPAD_NAME=$(basename "$IPAD_SRC")
      cp "$IPAD_SRC" "$REPORTS_DIR/$IPAD_NAME"
      IPAD_PATH="reports/$IPAD_NAME"
    fi

    # Build tags array JSON
    TAGS_JSON=$(echo "$TAGS" | python3 -c '
import sys, json
tags = [t.strip() for t in sys.stdin.read().split(",") if t.strip()]
print(json.dumps(tags, ensure_ascii=False))')

    # Inject into index.html via Python
    python3 << PYEOF
import re, json

with open("$INDEX","r",encoding="utf-8") as f:
    html = f.read()

# Find REPORTS array
m = re.search(r"const REPORTS = (\[.*?\]);(?=\s*//\s*=== END DATA ===)", html, re.DOTALL)
if not m:
    print("ERROR: REPORTS array marker not found"); exit(1)

# Parse existing reports (loose JSON5-ish via eval-safe manual parse)
arr_text = m.group(1)
# use json by replacing quotes if needed; the file uses double quotes already
try:
    reports = json.loads(arr_text)
except Exception:
    print("Could not parse REPORTS as JSON, falling back to regex injection.")
    reports = None

new_entry = {
    "id": "$ID",
    "date": "$DATE",
    "title": """$TITLE""",
    "summary": """$SUMMARY""",
    "tags": $TAGS_JSON,
    "pc": "$PC_PATH",
    "ipad": "$IPAD_PATH" if "$IPAD_PATH" else None,
    "new": True
}
# Remove None ipad
if not new_entry["ipad"]:
    del new_entry["ipad"]

if reports is not None:
    # Mark all existing as not-new
    for r in reports:
        r["new"] = False
    # Replace if id exists
    reports = [r for r in reports if r.get("id") != new_entry["id"]]
    reports.insert(0, new_entry)
    new_arr_text = json.dumps(reports, ensure_ascii=False, indent=2)
    # Convert to JS-style (true/false already same)
    new_html = html.replace(arr_text, new_arr_text)
    with open("$INDEX","w",encoding="utf-8") as f:
        f.write(new_html)
    print(f"Added/updated report '$ID'. Total reports: {len(reports)}")
else:
    exit(1)
PYEOF

    # auto push
    "$0" push "Add report: $TITLE"
    ;;

  remove)
    ID="$2"
    if [ -z "$ID" ]; then echo "Usage: $0 remove <id>"; exit 1; fi
    python3 << PYEOF
import re, json
with open("$INDEX","r",encoding="utf-8") as f:
    html = f.read()
m = re.search(r"const REPORTS = (\[.*?\]);(?=\s*//\s*=== END DATA ===)", html, re.DOTALL)
reports = json.loads(m.group(1))
reports = [r for r in reports if r.get("id") != "$ID"]
new_arr = json.dumps(reports, ensure_ascii=False, indent=2)
html = html.replace(m.group(1), new_arr)
with open("$INDEX","w",encoding="utf-8") as f:
    f.write(html)
print(f"Removed '$ID'. Remaining: {len(reports)}")
PYEOF
    "$0" push "Remove report: $ID"
    ;;

  push)
    MSG="${2:-Update reports}"
    cd "$REPO_DIR"
    git add -A
    if git diff --cached --quiet; then
      echo "No changes to commit."
      exit 0
    fi
    git commit -m "$MSG"
    git push -u origin main
    echo "✅ Pushed: $MSG"
    echo "🌐 https://whysosary-dot.github.io/investment-reports/"
    ;;

  list)
    python3 << PYEOF
import re, json
with open("$INDEX","r",encoding="utf-8") as f:
    html = f.read()
m = re.search(r"const REPORTS = (\[.*?\]);(?=\s*//\s*=== END DATA ===)", html, re.DOTALL)
if m:
    try:
        items = json.loads(m.group(1))
        for r in items:
            print(f"  - [{r['date']}] {r['id']}: {r['title']}")
    except Exception as e:
        print("Parse error:", e)
PYEOF
    ;;

  *)
    echo "Investment Reports — Auto Push CLI"
    echo ""
    echo "Commands:"
    echo "  add <id> <date> <title> <summary> <tags-csv> <pc-file> [ipad-file]"
    echo "      → Copy report files, inject metadata into index.html, commit & push"
    echo "  remove <id>"
    echo "      → Remove report entry, commit & push"
    echo "  push [msg]"
    echo "      → Commit any pending changes & push"
    echo "  list"
    echo "      → List all registered reports"
    echo ""
    echo "Site: https://whysosary-dot.github.io/investment-reports/"
    ;;
esac
