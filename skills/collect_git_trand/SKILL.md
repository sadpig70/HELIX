---
name: collect_git_trand
description: "GitHub Trending 수집 스킬. 사용자가 GitHub 트렌딩, daily/weekly/monthly, 일간/주간/월간, stars gained, 스타 증가량, 많이 늘어난 저장소 수집/리포트 저장을 요청할 때 사용한다. GitHub Trending repositories 페이지를 직접 가져와 기간별 repo, URL, 설명, 언어, 총 stars, forks, 기간 증가 stars를 Markdown/JSON/CSV로 저장한다."
user-invocable: true
argument-hint: "daily|weekly|monthly|all [--top N] [--output-dir PATH]"
---

# collect_git_trand

GitHub Trending repositories에서 일간/주간/월간 기준 star 증가량이 큰 저장소를 수집해 로컬 파일로 저장한다.

## Workflow

1. 현재 워크스페이스 루트에서 실행한다.
2. 기본 출력은 `_workspace/`에 저장한다.
3. 기간 기본값은 `daily weekly monthly` 전체다.
4. 수집 후 Markdown을 열어 증가 stars가 비어 있지 않은지 확인한다.

```powershell
python skills/collect_git_trand/scripts/collect_github_trending.py --output-dir _workspace
```

옵션:

```powershell
python skills/collect_git_trand/scripts/collect_github_trending.py --period daily --period weekly --top 25 --output-dir _workspace
```

## Output

파일명은 실행일(KST) 기준이다.

- `github_trending_star_growth_YYYYMMDD.md`
- `github_trending_star_growth_YYYYMMDD.json`
- `github_trending_star_growth_YYYYMMDD.csv`

Markdown에는 기간별 표와 복수 기간 중복 출현 저장소를 포함한다.

## Validation

- `rows=N`이 0보다 커야 한다.
- Markdown의 `stars gained` 열이 채워져 있어야 한다.
- 원본 링크는 다음 3개를 명시한다.
  - `https://github.com/trending?since=daily`
  - `https://github.com/trending?since=weekly`
  - `https://github.com/trending?since=monthly`

## Notes

- GitHub Trending 페이지의 HTML class는 변동될 수 있다. `period_stars`가 비어 있으면 `scripts/collect_github_trending.py`의 `float-sm-right`/description 파서를 먼저 점검한다.
- 이 스킬은 GitHub API가 아니라 공개 Trending HTML을 사용한다. GitHub Trending 자체가 반환하는 repo 수가 25개보다 적을 수 있다.

