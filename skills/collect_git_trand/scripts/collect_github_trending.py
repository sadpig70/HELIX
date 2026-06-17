from __future__ import annotations

import argparse
import csv
import html
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


KST = timezone(timedelta(hours=9))
PERIOD_LABELS = {
    "daily": "일간",
    "weekly": "주간",
    "monthly": "월간",
}


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def number_from_text(value: str) -> int | None:
    match = re.search(r"([\d,]+)", value)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def fetch(period: str) -> str:
    url = f"https://github.com/trending?since={period}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def parse_article(block: str, period: str, rank: int) -> dict[str, Any]:
    repo_match = re.search(r'<h2[^>]*>\s*<a[^>]+href="/([^"]+)"[^>]*>(.*?)</a>', block, re.S)
    if not repo_match:
        raise ValueError("repo link not found")

    repo_path = repo_match.group(1).strip("/")
    repo_name = strip_tags(repo_match.group(2)).replace(" / ", "/").replace(" ", "")
    desc_match = re.search(r'<p[^>]+class="[^"]*color-fg-muted[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.S)
    language_match = re.search(r'itemprop="programmingLanguage"[^>]*>(.*?)</span>', block, re.S)
    star_match = re.search(rf'href="/{re.escape(repo_path)}/stargazers"[^>]*>(.*?)</a>', block, re.S)
    fork_match = re.search(rf'href="/{re.escape(repo_path)}/forks"[^>]*>(.*?)</a>', block, re.S)
    period_star_match = re.search(r'<span[^>]+class="[^"]*float-sm-right[^"]*"[^>]*>\s*(.*?)\s*</span>', block, re.S)
    period_star_text = strip_tags(period_star_match.group(1)) if period_star_match else ""

    return {
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "rank": rank,
        "repo": repo_name or repo_path,
        "url": f"https://github.com/{repo_path}",
        "description": strip_tags(desc_match.group(1)) if desc_match else "",
        "language": strip_tags(language_match.group(1)) if language_match else "",
        "total_stars": number_from_text(strip_tags(star_match.group(1))) if star_match else None,
        "forks": number_from_text(strip_tags(fork_match.group(1))) if fork_match else None,
        "period_stars_text": period_star_text,
        "period_stars": number_from_text(period_star_text),
    }


def collect(periods: list[str], top: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for period in periods:
        html_text = fetch(period)
        articles = re.findall(r'<article class="Box-row">(.*?)</article>', html_text, re.S)
        for rank, block in enumerate(articles[:top], start=1):
            rows.append(parse_article(block, period, rank))
    return rows


def write_outputs(rows: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(KST)
    stamp = now.strftime("%Y-%m-%d %H:%M KST")
    date = now.strftime("%Y%m%d")
    md_path = output_dir / f"github_trending_star_growth_{date}.md"
    json_path = output_dir / f"github_trending_star_growth_{date}.json"
    csv_path = output_dir / f"github_trending_star_growth_{date}.csv"

    periods = list(dict.fromkeys(str(row["period"]) for row in rows))
    by_period = {period: [row for row in rows if row["period"] == period] for period in periods}
    seen: dict[str, list[str]] = {}
    for row in rows:
        seen.setdefault(str(row["repo"]), []).append(str(row["period_label"]))
    repeats = {repo: labels for repo, labels in seen.items() if len(labels) > 1}

    lines = [
        "# GitHub Trending Star Growth",
        "",
        f"- 수집 시각: {stamp}",
        "- 기준: GitHub Trending repositories, `since=daily|weekly|monthly`",
        "- 해석: GitHub Trending의 기간별 정렬을 기간 내 star 증가량 순위로 사용",
        "- 원본: [daily](https://github.com/trending?since=daily), [weekly](https://github.com/trending?since=weekly), [monthly](https://github.com/trending?since=monthly)",
        "",
    ]

    for period in periods:
        rows_for_period = by_period[period]
        lines.extend([f"## {PERIOD_LABELS[period]} Top {len(rows_for_period)}", ""])
        lines.append("| rank | repo | stars gained | total stars | language | description |")
        lines.append("|---:|---|---:|---:|---|---|")
        for row in rows_for_period:
            desc = str(row["description"]).replace("|", "\\|")
            if len(desc) > 120:
                desc = desc[:117] + "..."
            lines.append(
                f"| {row['rank']} | [{row['repo']}]({row['url']}) | "
                f"{row['period_stars'] or ''} | {row['total_stars'] or ''} | "
                f"{row['language'] or ''} | {desc} |"
            )
        lines.append("")

    lines.extend(["## 기간 중복 출현", ""])
    if repeats:
        lines.append("| repo | periods |")
        lines.append("|---|---|")
        for repo, labels in sorted(repeats.items()):
            url = next(str(row["url"]) for row in rows if row["repo"] == repo)
            lines.append(f"| [{repo}]({url}) | {', '.join(labels)} |")
    else:
        lines.append("- 중복 출현 저장소 없음.")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return [md_path, json_path, csv_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect GitHub Trending star growth into Markdown/JSON/CSV.")
    parser.add_argument("--period", action="append", choices=sorted(PERIOD_LABELS), help="Period to collect. Repeatable.")
    parser.add_argument("--top", type=int, default=25, help="Maximum repositories per period.")
    parser.add_argument("--output-dir", default="_workspace", help="Output directory.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    periods = args.period or ["daily", "weekly", "monthly"]
    rows = collect(periods, max(1, args.top))
    outputs = write_outputs(rows, Path(args.output_dir))
    for output in outputs:
        print(output)
    print(f"rows={len(rows)}")
    missing_growth = [row["repo"] for row in rows if not row.get("period_stars")]
    if missing_growth:
        print(f"warning: missing period_stars for {len(missing_growth)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

