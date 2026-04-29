# Investment Reports

한국·해외 투자 분석 리포트 모음.

🌐 **Live Site:** https://whysosary-dot.github.io/investment-reports/

## 구조
```
investment-reports/
├── index.html             ← 메인 리스트 페이지 (검색·필터·테마 토글)
├── reports/               ← 개별 리포트 HTML 파일
│   ├── *_PC.html          ← PC용 화이트 테마
│   └── *_iPad.html        ← 아이패드용 다크 테마
└── publish_report.py      ← 자동 commit & push 스크립트
```

## 첫 사용 시 PAT 등록
GitHub Personal Access Token을 환경변수 또는 로컬 파일에 저장:

```bash
# 옵션 1: 환경변수
export GH_PAT='ghp_xxxxxxxxxxxxxxxxxxxxxxxx'

# 옵션 2: 로컬 파일 (한 번만 하면 됨)
echo 'ghp_xxxxxxxxxxxxxxxxxxxxxxxx' > ~/.invreports_pat
chmod 600 ~/.invreports_pat
```

## 새 리포트 추가하기

```bash
python3 publish_report.py add \
  --id "20260430-samsung-electronics" \
  --date "2026-04-30" \
  --title "삼성전자 2025 사업보고서 분석" \
  --summary "DS·DX·하만 부문별 실적, 메모리 사이클 분석..." \
  --tags "KR,종목분석,반도체" \
  --pc "/path/to/리포트_PC.html" \
  --ipad "/path/to/리포트_iPad.html"
```

스크립트는 자동으로:
1. 임시 디렉토리에 repo clone
2. 리포트 파일을 `reports/`에 복사
3. `index.html`의 REPORTS 배열에 메타데이터 추가
4. 기존 NEW 배지 제거 (최신 1개만 NEW)
5. `git commit` + `git push origin main`
6. GitHub Pages 자동 빌드 (1~2분 후 사이트 반영)

## 다른 명령어
```bash
python3 publish_report.py list                            # 모든 리포트 조회
python3 publish_report.py remove --id "20260430-..."      # 리포트 삭제
```

## 태그 컨벤션
- `KR` / `US` — 국가 (필터 키)
- `Sector` / `Macro` / `종목분석` — 분석 유형
- `반도체` / `2차전지` / `조선` ... — 산업/테마

⚠️ 자동 생성 분석 — 투자 권유가 아닙니다.
