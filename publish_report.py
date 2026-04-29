#!/usr/bin/env python3
"""
Investment Reports — Auto Publisher

새 리포트를 GitHub Pages 사이트에 자동 배포합니다.
세션 마운트의 git 권한 이슈를 우회하기 위해 임시 디렉토리에서 git 작업을 수행합니다.

사용법:
  python3 publish_report.py add \\
    --id "20260429-sangshin-vs-shinheung" \\
    --date "2026-04-29" \\
    --title "상신이디피 vs 신흥에스이씨 비교분석" \\
    --summary "사업보고서 6개년 매출·캐파·가동률 비교..." \\
    --tags "KR,Sector,2차전지" \\
    --pc "/path/to/PC.html" \\
    --ipad "/path/to/iPad.html"

  python3 publish_report.py list
  python3 publish_report.py remove --id "20260429-sangshin-vs-shinheung"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/whysosary-dot/investment-reports.git"
USER_EMAIL = "whysosary@naver.com"
USER_NAME = "리송"
PAGES_URL = "https://whysosary-dot.github.io/investment-reports/"

# PAT from env or local config file (~/.invreports_pat)
def _load_pat():
    p = os.environ.get("GH_PAT") or os.environ.get("INVREPORTS_PAT")
    if p:
        return p
    cfg = os.path.expanduser("~/.invreports_pat")
    if os.path.isfile(cfg):
        return open(cfg).read().strip()
    sys.exit(
        "GitHub PAT not found. Set env var GH_PAT or save to ~/.invreports_pat\n"
        "  export GH_PAT='ghp_xxx'\n"
        "  echo 'ghp_xxx' > ~/.invreports_pat && chmod 600 ~/.invreports_pat"
    )

PAT = _load_pat()
PAT_URL = REPO_URL.replace("https://", f"https://whysosary-dot:{PAT}@")


def run(cmd, cwd=None, check=True, capture=True):
    """Run shell command."""
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=capture, text=True)
    if capture:
        if r.stdout.strip():
            print(r.stdout.strip())
        if r.stderr.strip():
            print(r.stderr.strip(), file=sys.stderr)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed (exit {r.returncode})")
    return r


def clone_repo(workdir):
    """Clone the repo into workdir."""
    run(f'git clone "{PAT_URL}" "{workdir}"', capture=True)
    run(f'git config user.email "{USER_EMAIL}"', cwd=workdir)
    run(f'git config user.name "{USER_NAME}"', cwd=workdir)


def parse_reports(html: str):
    m = re.search(r"const REPORTS = (\[.*?\]);(?=\s*//\s*=== END DATA ===)", html, re.DOTALL)
    if not m:
        raise RuntimeError("REPORTS array marker not found in index.html")
    return m.group(1), json.loads(m.group(1))


def write_reports(html: str, reports: list) -> str:
    arr_text, _ = parse_reports(html)
    new_arr = json.dumps(reports, ensure_ascii=False, indent=2)
    return html.replace(arr_text, new_arr)


def cmd_add(args):
    if not os.path.isfile(args.pc):
        sys.exit(f"PC file not found: {args.pc}")
    if args.ipad and not os.path.isfile(args.ipad):
        sys.exit(f"iPad file not found: {args.ipad}")

    with tempfile.TemporaryDirectory(prefix="invreports-") as tmp:
        repo = os.path.join(tmp, "repo")
        clone_repo(repo)

        # Copy report files
        reports_dir = os.path.join(repo, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        pc_name = os.path.basename(args.pc)
        shutil.copy2(args.pc, os.path.join(reports_dir, pc_name))
        ipad_name = None
        if args.ipad:
            ipad_name = os.path.basename(args.ipad)
            shutil.copy2(args.ipad, os.path.join(reports_dir, ipad_name))

        # Update index.html
        idx_path = os.path.join(repo, "index.html")
        with open(idx_path, encoding="utf-8") as f:
            html = f.read()
        _, reports = parse_reports(html)

        # Mark all old as not new
        for r in reports:
            r["new"] = False

        # Remove duplicate by id
        reports = [r for r in reports if r.get("id") != args.id]

        new_entry = {
            "id": args.id,
            "date": args.date,
            "title": args.title,
            "summary": args.summary,
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "pc": f"reports/{pc_name}",
            "new": True,
        }
        if ipad_name:
            new_entry["ipad"] = f"reports/{ipad_name}"

        reports.insert(0, new_entry)

        new_html = write_reports(html, reports)
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(new_html)

        # Commit & push
        run("git add -A", cwd=repo)
        run(f'git commit -m "Add report: {args.title}"', cwd=repo)
        run("git push origin main", cwd=repo)

    print()
    print("✅ Published successfully!")
    print(f"🌐 {PAGES_URL}")
    print(f"📄 {PAGES_URL}reports/{pc_name}")


def cmd_list(args):
    with tempfile.TemporaryDirectory(prefix="invreports-") as tmp:
        repo = os.path.join(tmp, "repo")
        clone_repo(repo)
        idx_path = os.path.join(repo, "index.html")
        with open(idx_path, encoding="utf-8") as f:
            html = f.read()
        _, reports = parse_reports(html)
        print(f"\n총 {len(reports)}개 리포트:\n")
        for r in reports:
            tags = "·".join(r.get("tags", []))
            print(f"  [{r['date']}] {r['id']}")
            print(f"    {r['title']}")
            print(f"    Tags: {tags}\n")


def cmd_remove(args):
    with tempfile.TemporaryDirectory(prefix="invreports-") as tmp:
        repo = os.path.join(tmp, "repo")
        clone_repo(repo)

        idx_path = os.path.join(repo, "index.html")
        with open(idx_path, encoding="utf-8") as f:
            html = f.read()
        _, reports = parse_reports(html)
        target = next((r for r in reports if r.get("id") == args.id), None)
        if not target:
            sys.exit(f"Report id not found: {args.id}")

        # Delete files
        for key in ("pc", "ipad"):
            p = target.get(key)
            if p:
                fp = os.path.join(repo, p)
                if os.path.isfile(fp):
                    os.remove(fp)

        reports = [r for r in reports if r.get("id") != args.id]
        new_html = write_reports(html, reports)
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(new_html)

        run("git add -A", cwd=repo)
        run(f'git commit -m "Remove report: {args.id}"', cwd=repo)
        run("git push origin main", cwd=repo)

    print(f"✅ Removed report: {args.id}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="Add new report and push")
    a.add_argument("--id", required=True, help="Unique slug, e.g. 20260429-sangshin-vs-shinheung")
    a.add_argument("--date", required=True, help="YYYY-MM-DD")
    a.add_argument("--title", required=True)
    a.add_argument("--summary", required=True)
    a.add_argument("--tags", required=True, help="Comma-separated, e.g. KR,Sector,2차전지")
    a.add_argument("--pc", required=True, help="Path to PC (white) HTML file")
    a.add_argument("--ipad", help="Path to iPad (dark) HTML file (optional)")
    a.set_defaults(func=cmd_add)

    sub.add_parser("list", help="List all reports").set_defaults(func=cmd_list)

    r = sub.add_parser("remove", help="Remove a report by id")
    r.add_argument("--id", required=True)
    r.set_defaults(func=cmd_remove)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
