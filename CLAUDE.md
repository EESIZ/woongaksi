# 노션우렁각시 (woongaksi)

AI 에이전트(OpenClaw 등)와 Notion을 업무 관리용으로 같이 쓸 때, AI가 Notion API를 직접 호출하면서 생기는 **토큰 비용 폭발**과 **메모리 오염**(낡은 데이터로 답변)을 해결하는 백그라운드 릴레이 데몬.

**LLM 토큰 소모 제로.** 순수 HTTP로 Notion 폴링 → 변경 감지 → 텔레그램 전송.

## 이 프로젝트가 해결하는 문제

```
문제: AI 에이전트가 Notion API를 직접 호출
  → 매 질문마다 tool use + 파싱 = 수천 토큰
  → 또는 조회 결과를 메모리에 저장 → 낡은 정보로 답변

해결: 우렁각시가 5분마다 Notion 폴링 (토큰 제로)
  → 변경사항만 텔레그램으로 전송
  → AI가 채팅 컨텍스트에서 이미 인지 → API 재호출 불필요
```

## AI 에이전트와의 연동 방식

```
[유저]                    [우렁각시]                [AI 에이전트]
  │                         │                          │
  │  Notion 수정             │                          │
  │                    5분 내 감지 (Notion API)         │
  │              텔레그램 전송 ──────────────────────→ │
  │              "✏️ 보고서: 진행중→완료"               │
  │                         │                   컨텍스트에 반영
  │  "남은 업무?" ─────────────────────────────────→ │
  │                         │           API 안 쳐도 이미 알고 있음
  │←───────────────────────────── "보고서 완료, 3건 남음"
```

**핵심:** 우렁각시와 AI 에이전트가 **같은 텔레그램 채팅방**을 공유해야 함.

### AI 시스템 프롬프트에 추가해야 할 규칙

AI 에이전트의 시스템 프롬프트(SOUL.md 등)에 아래를 추가해야 우렁각시 메시지를 올바르게 활용함:

```markdown
## 우렁각시 릴레이
- 📋/📊 이모지로 시작하는 텔레그램 알림 = Notion 실시간 변경사항 (5분 이내)
- 이 데이터는 메모리보다 우선한다
- 최근 릴레이로 받은 데이터가 있으면 Notion API를 다시 호출하지 않는다
- 업무 상태를 장기 메모리에 저장하지 않는다 (항상 릴레이/API 기준)
```

## 아키텍처

```
config.yaml (DB 정의)  ──→  scheduler.py (APScheduler 루프)
         │                        │
         ▼                        ▼ DB별
      config.py               client.py (Notion API 조회)
     (YAML + env)                 │
                                  ▼
                             differ.py (캐시 비교)
                                  │
                             변경 있음?
                               yes │
                                  ▼
                           formatter.py (HTML 변환)
                                  │
                                  ▼
                           telegram.py (Bot API 전송)
```

## 파일 맵

| 파일 | 역할 | 주요 export |
|------|------|------------|
| `__main__.py` | CLI 진입점, 로깅, 시그널 처리 | `main()` |
| `config.py` | YAML + env → `Config` dataclass | `Config`, `load_config()` |
| `client.py` | Notion API 범용 클라이언트, 14종 프로퍼티 | `query_database()` |
| `differ.py` | JSON 캐시 + diff 계산 | `DiffResult`, `compute_diff()` |
| `formatter.py` | DiffResult → 텔레그램 HTML | `format_changes()` |
| `telegram.py` | 메시지 전송, 4096자 자동 분할, 3회 재시도 | `send_message()` |
| `scheduler.py` | APScheduler 오케스트레이터 | `poll_and_notify()`, `create_scheduler()` |

## 설정 구조

**환경변수** (시크릿 — 절대 YAML에 넣지 말 것):
- `NOTION_API_KEY` — Notion integration 토큰 (필수)
- `TELEGRAM_BOT_TOKEN` — @BotFather 토큰 (필수)
- `TELEGRAM_CHAT_ID` — 대상 채팅 ID (필수)
- `POLL_INTERVAL_MINUTES` — YAML 값 덮어쓰기 (선택)
- `WOONGAKSI_CONFIG` — 설정 파일 경로 (기본: `config.yaml`)
- `WOONGAKSI_LOG` — 로그 경로 (기본: `/tmp/woongaksi.log`)
- `WOONGAKSI_CACHE` — 캐시 디렉토리 (기본: `./cache`)

**config.yaml** (DB 정의):
```yaml
databases:
  - name: "내부이름"            # 캐시 키
    id: "notion-db-uuid"       # DB ID
    emoji: "📋"                # 알림 이모지
    label: "표시이름"           # 알림 제목
    title_property: "Name"     # 제목 프로퍼티
    tracked_properties: [...]  # 추적 대상 (비우면 전체)
    filter: { ... }            # Notion API 필터 (선택)
```

## 자주 하는 수정

### DB 추가
`config.yaml`의 `databases:` 리스트에 항목 추가 → 데몬 재시작.

### Notion 프로퍼티 타입 추가
`client.py` → `_extract_value()` 에 `if ptype == "새타입":` 분기 추가.

### 알림 채널 추가 (Slack, Discord 등)
1. `woongaksi/slack.py` 생성 — `send_message(text)` 구현
2. `scheduler.py` → `_poll_db()` 에서 telegram과 함께 호출

### 알림 포맷 변경
`formatter.py` → `format_changes()`. 텔레그램 HTML 사용 (`<b>`, `<i>`, `<code>`).
반드시 `_escape_html()` 으로 유저 데이터 이스케이프.

## 제약사항
- 텔레그램 메시지 4096자 제한 (자동 분할 처리됨)
- Notion API rate limit: 3 req/sec — 쓰로틀링 미구현 (DB 수가 적으면 문제없음)
- 최초 실행은 캐시 시딩만 하고 알림 안 보냄 (정상 동작)
- 캐시: `./cache/{db_name}_state.json` (JSON)
- APScheduler `max_instances=1` — 이전 폴링 완료 전 다음 폴링 안 시작

## 절대 하지 말 것
- API 키를 config.yaml에 넣기 → 환경변수만 사용
- 절대경로 임포트 (`from config import ...`) → 상대 임포트 (`from .config import ...`)
- 우렁각시에 LLM 호출 추가 → 이 프로젝트의 존재 이유가 "토큰 제로"임
