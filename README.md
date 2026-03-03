# 노션우렁각시 (woongaksi)

> 사람이 Notion을 수정하면 AI 에이전트가 자동으로 알게 해주는 백그라운드 릴레이 데몬.
> LLM 토큰 제로. API 키 하나. 5분 세팅.

## 이게 왜 필요한가

AI 에이전트(OpenClaw, Claude 등)와 Notion을 업무 관리용으로 같이 쓰면 두 가지 문제가 생깁니다:

**문제 1: 토큰 비용 폭발**
```
유저: "오늘 할 일 뭐야?"
→ AI가 Notion API 호출 (tool use 토큰 소모)
→ 응답 파싱 (input 토큰 소모)
→ 답변 생성 (output 토큰 소모)
→ 매번 반복 = 하루 수만 토큰
```

**문제 2: 메모리 오염**
```
AI가 Notion 조회 결과를 벡터 메모리에 저장
→ 다음 질문에 API 안 치고 낡은 메모리로 답변
→ "그 업무 아직 진행중이에요" (실제로는 이미 완료됨)
```

**우렁각시의 해법:**
```
유저가 Notion에서 업무 수정
→ 우렁각시가 5분 내 감지 (LLM 토큰 제로)
→ 텔레그램 채팅에 변경사항 자동 전송
→ AI 에이전트가 채팅 컨텍스트에서 이미 인지
→ 별도 API 호출 없이 최신 상태 파악
```

### 핵심 장점

| 항목 | AI가 직접 Notion 조회 | 우렁각시 사용 |
|------|---------------------|--------------|
| 토큰 비용 | 매 질문마다 수천 토큰 | **제로** |
| 데이터 신선도 | 질문할 때만 조회 | 5분 내 자동 반영 |
| 메모리 오염 | 낡은 데이터로 답변 위험 | 채팅 컨텍스트만 사용, 오염 없음 |
| 응답 속도 | API 왕복 대기 | 이미 인지 → 즉답 |
| AI 세션 부하 | 크론 조회 시 세션 오염 | AI 세션과 완전 분리 |

## 동작 흐름

```
[유저]                    [우렁각시]                [AI 에이전트]
  │                         │                          │
  │  Notion에서 업무 수정    │                          │
  │  (상태: 진행중→완료)     │                          │
  │                         │                          │
  │                    5분 내 감지                      │
  │                    (Notion API 직접 조회)           │
  │                    변경사항 비교                    │
  │                         │                          │
  │              텔레그램 메시지 전송 ─────────────────→│
  │              "✏️ 보고서 작성: 진행중→완료"          │
  │                         │                     컨텍스트에 반영
  │                         │                          │
  │  "오늘 남은 업무 뭐야?" ──────────────────────────→│
  │                         │                          │
  │                         │      이미 알고 있음, API 호출 불필요
  │←──────────────────────── "보고서 완료, 남은 건 3건" │
```

## 필수 환경

| 항목 | 요구사항 |
|------|---------|
| Python | 3.10 이상 |
| OS | Linux (systemd), macOS, Windows |
| Notion | Integration 토큰 ([생성 방법](#1-notion-integration-생성)) |
| Telegram | Bot 토큰 + Chat ID ([생성 방법](#2-telegram-봇-생성)) |
| AI 에이전트 | OpenClaw 또는 텔레그램 기반 AI 봇 (같은 채팅방 공유) |
| 네트워크 | Notion API + Telegram API 접근 가능 |

## 설치 가이드

### 0. 사전 조건 확인

```bash
python3 --version    # 3.10 이상인지 확인
pip --version        # pip 사용 가능한지 확인
```

### 1. Notion Integration 생성

1. https://www.notion.so/profile/integrations 접속
2. **"새 API 통합"** 클릭
3. 이름 입력 (예: "우렁각시")
4. **기능 > 콘텐츠 기능** → "콘텐츠 읽기" 체크 (쓰기는 불필요)
5. **제출** → 표시되는 토큰 복사 (secret_xxx...)
6. **모니터링할 Notion DB 페이지에서** → 우상단 `⋯` → **연결** → 방금 만든 통합 선택

> **이 단계를 빠뜨리면 API가 403 에러를 반환합니다.**
> DB마다 개별적으로 연결해야 합니다.

### 2. Telegram 봇 생성

1. 텔레그램에서 **@BotFather** 검색 → `/newbot` 입력
2. 봇 이름, 유저네임 입력 → **토큰** 복사 (123456789:ABCdef...)
3. **Chat ID 확인:**
   - 봇에게 아무 메시지 전송
   - 브라우저에서 `https://api.telegram.org/bot{토큰}/getUpdates` 접속
   - 응답에서 `"chat":{"id": 123456789}` 확인
4. **AI 에이전트와 같은 채팅방에 봇 추가** (그룹 채팅 사용 시)

> AI 에이전트(OpenClaw 등)가 같은 텔레그램 채팅을 보고 있어야
> 우렁각시가 보낸 변경 알림을 AI가 인지할 수 있습니다.

### 3. 설치 및 설정

```bash
# 클론
git clone https://github.com/yourname/woongaksi.git
cd woongaksi

# 설치
pip install .

# 설정 파일 복사
cp config.example.yaml config.yaml
cp .env.example .env
```

**config.yaml 편집** — 모니터링할 Notion DB 정의:

```yaml
poll_interval_minutes: 5

databases:
  - name: tasks
    id: "여기에-노션-DB-ID-붙여넣기"
    emoji: "📋"
    label: "업무"
    title_property: "업무명"        # 본인 DB의 제목 프로퍼티명
    tracked_properties:
      - "상태"                      # 본인 DB의 프로퍼티명들
      - "우선순위"
      - "마감일"
    filter:
      property: "상태"
      select:
        does_not_equal: "완료"
```

**.env 편집** — 시크릿:

```bash
NOTION_API_KEY=secret_실제토큰
TELEGRAM_BOT_TOKEN=실제봇토큰
TELEGRAM_CHAT_ID=실제채팅ID
```

### 4. 테스트 실행

```bash
# 환경변수 로드 후 실행
export $(grep -v '^#' .env | xargs)
woongaksi --config config.yaml
```

정상 동작 시 출력:
```
[2026-03-03 14:00:00 KST] INFO woongaksi: === 노션우렁각시 v0.1.0 시작 ===
[2026-03-03 14:00:00 KST] INFO woongaksi: 모니터링 DB 1개, 폴링 간격 5분
[2026-03-03 14:00:00 KST] INFO woongaksi:   📋 업무 [여기에-노...]
[2026-03-03 14:00:01 KST] INFO woongaksi: 최초 폴링 실행...
[2026-03-03 14:00:02 KST] INFO woongaksi.client: [tasks] 8건 조회
[2026-03-03 14:00:02 KST] INFO woongaksi: [tasks] 최초 실행, 캐시 시딩 (8건)
[2026-03-03 14:00:02 KST] INFO woongaksi: 스케줄러 시작. 다음 폴링 5분 후.
```

**검증:** Notion에서 아무 항목의 상태를 변경 → 5분 내 텔레그램에 알림 도착 확인.

### 5. systemd 서비스 등록 (Linux)

```bash
# 설정 디렉토리 생성
mkdir -p ~/.config/woongaksi
cp config.yaml ~/.config/woongaksi/

# 서비스 파일 복사 & 편집
cp examples/woongaksi.service ~/.config/systemd/user/
# → Environment= 줄에 실제 토큰 입력

# 서비스 시작
systemctl --user daemon-reload
systemctl --user enable --now woongaksi

# 확인
systemctl --user status woongaksi
journalctl --user -u woongaksi -f
```

## AI 에이전트 연동 설정

우렁각시가 텔레그램에 보내는 메시지를 AI 에이전트가 **신뢰할 수 있는 실시간 데이터**로 인식하도록 시스템 프롬프트(SOUL.md)에 다음 규칙을 추가하세요:

```markdown
## Notion 연동 규칙

### 우렁각시 릴레이 메시지
- 텔레그램 채팅에 📋/📊 이모지로 시작하는 변경 알림이 도착하면
  이것은 **우렁각시 데몬이 Notion DB의 실제 변경사항을 감지하여 전송한 것**이다.
- 이 데이터는 실시간(5분 이내)이므로 메모리보다 우선한다.
- 우렁각시 릴레이 메시지가 도착하면 관련 메모리를 업데이트한다.

### Notion API 직접 호출 최소화
- 최근 우렁각시 알림으로 받은 데이터가 있으면 API를 다시 호출하지 않는다.
- API 직접 호출은 유저가 명시적으로 "Notion 조회해줘"라고 할 때만 한다.
- 업무 상태를 물어보면 가장 최근 우렁각시 알림 기준으로 답변한다.

### 메모리 오염 방지
- Notion에서 조회한 업무 상태/진행률은 장기 메모리에 저장하지 않는다.
- 업무 데이터의 Single Source of Truth는 항상 Notion이다.
- 우렁각시 알림 = Notion 실제 상태로 간주한다.
```

## 설정 레퍼런스

### 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `NOTION_API_KEY` | O | Notion Integration 토큰 |
| `TELEGRAM_BOT_TOKEN` | O | @BotFather에서 받은 봇 토큰 |
| `TELEGRAM_CHAT_ID` | O | 메시지 보낼 채팅 ID |
| `POLL_INTERVAL_MINUTES` | X | YAML 값 덮어쓰기 (기본 5) |
| `WOONGAKSI_CONFIG` | X | 설정 파일 경로 (기본 `config.yaml`) |
| `WOONGAKSI_LOG` | X | 로그 파일 (기본 `/tmp/woongaksi.log`) |
| `WOONGAKSI_CACHE` | X | 캐시 디렉토리 (기본 `./cache`) |

### config.yaml DB 항목

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | O | 내부 식별자 (캐시 파일명) |
| `id` | O | Notion 데이터베이스 ID |
| `emoji` | X | 알림 접두 이모지 (기본 📄) |
| `label` | X | 알림 표시 이름 |
| `title_property` | X | 제목으로 쓸 프로퍼티 (기본 `Name`) |
| `tracked_properties` | X | 추적할 프로퍼티 목록 (비우면 전체) |
| `filter` | X | Notion API 필터 (생략하면 전체 조회) |

### 지원하는 Notion 프로퍼티 타입

title, rich_text, select, multi_select, date, number, checkbox, status, url, email, phone_number, people, relation, formula, rollup

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `403 Forbidden` | Notion DB에 Integration 연결 안 됨 | DB 페이지 → ⋯ → 연결 → 통합 선택 |
| `401 Unauthorized` | 토큰 오류 | NOTION_API_KEY 재확인 |
| 알림이 안 옴 | 변경 없음 / Chat ID 오류 | 로그 확인 + Chat ID 재확인 |
| 최초 실행 시 알림 없음 | 정상 (캐시 시딩) | 두 번째 폴링부터 알림 시작 |
| 동일 변경 반복 알림 | 캐시 파일 손상 | `cache/` 디렉토리 삭제 후 재시작 |

## License

MIT
