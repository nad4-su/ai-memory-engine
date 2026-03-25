# AI Memory Engine — Architecture

## Vision
개인 AI 에이전트를 위한 **장기 기억 + 선제 제안 시스템**.
사용자의 대화/노트/북마크를 학습하여 관심사를 파악하고,
매일 아침 맞춤형 인사이트와 기회를 선제적으로 제안한다.

## Target Users
- AI 에이전트 운영자 (OpenClaw, LangChain, AutoGPT 등)
- 개인 지식 관리자 (Obsidian, Notion 사용자)
- 사업 기회를 체계적으로 추적하고 싶은 1인 사업자/개발자

## Core Principles
1. **Provider Agnostic**: OpenAI, Anthropic, Google 교체 가능
2. **MSA**: 서비스별 독립 컨테이너, 독립 배포
3. **5-min Setup**: `git clone → .env → docker compose up -d`
4. **Privacy First**: 모든 데이터 로컬 저장, 외부 전송 없음

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Memory Engine                      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Frontend (port 3080)                 │   │
│  │  프로필 뷰 | 제안 피드 | 검색 | 설정            │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────▼───────────────────────────────┐   │
│  │              API Gateway (port 8080)              │   │
│  │  /api/v1/profile | /search | /suggestions        │   │
│  │  /ingest | /health                               │   │
│  └───┬──────────┬──────────┬──────────┬─────────────┘   │
│      │          │          │          │                   │
│  ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼──────────┐       │
│  │Ingest │ │Profile│ │Advisor│ │ Memory Store  │       │
│  │Service│ │  or   │ │Service│ │  (Qdrant)     │       │
│  │       │ │Service│ │       │ │               │       │
│  │ 수집  │ │ 분석  │ │ 제안  │ │  벡터 검색    │       │
│  └───┬───┘ └───┬───┘ └───┬───┘ └───────────────┘       │
│      │         │         │                               │
│  ┌───▼─────────▼─────────▼──────────────────────────┐   │
│  │              LLM Router                           │   │
│  │  OpenAI | Anthropic | Google | Ollama (local)     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              PostgreSQL (port 5432)               │   │
│  │  profiles | suggestions | interests | decisions   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Services

### 1. API Gateway (`api-gateway/`)
- **Port**: 8080
- **Tech**: FastAPI
- **역할**: 모든 API 요청 라우팅, 인증, CORS
- **엔드포인트**:
  - `GET /api/v1/health` — 시스템 상태
  - `POST /api/v1/ingest` — 데이터 수집 (대화/노트)
  - `GET /api/v1/profile` — 사용자 프로필 조회
  - `GET /api/v1/profile/interests` — 관심사 목록
  - `GET /api/v1/profile/patterns` — 행동 패턴
  - `POST /api/v1/search` — 벡터 검색
  - `GET /api/v1/suggestions` — 오늘의 제안 목록
  - `POST /api/v1/suggestions/{id}/feedback` — 제안 피드백
  - `GET /api/v1/settings` — 설정 조회/변경

### 2. Ingest Service (`ingest-service/`)
- **역할**: 다양한 소스에서 데이터 수집 + 벡터화
- **소스**:
  - 대화 로그 (JSON/JSONL)
  - Obsidian Vault (마크다운)
  - 북마크 (Karakeep/Raindrop API)
  - 웹 클리핑 (URL → 본문 추출)
- **처리 흐름**:
  1. 원본 텍스트 수집
  2. 청킹 (512 토큰 단위, 128 오버랩)
  3. LLM Router로 임베딩 생성
  4. Qdrant에 벡터 저장
  5. PostgreSQL에 메타데이터 저장

### 3. Profiler Service (`profiler-service/`)
- **역할**: 사용자 행동 분석 → 프로필 자동 갱신
- **스케줄**: 매일 자정 (cron)
- **분석 항목**:
  - 관심사 태그 추출 (최근 7일 대화에서)
  - 관심 강도 계산 (언급 횟수 × 최신성 가중치)
  - 시간 패턴 감지 (요일별/시간대별 활동)
  - 의사결정 이력 (승인/거절/보류 비율)
  - 관심사 변화 트렌드 (상승/하락/신규)
- **출력**: `user_profile` JSON → PostgreSQL

### 4. Advisor Service (`advisor-service/`)
- **역할**: 선제 제안 생성
- **스케줄**: 매일 아침 (설정 가능, 기본 08:00)
- **프로세스**:
  1. 프로필 읽기 → 현재 TOP 관심사 추출
  2. RAG 검색 → 관련 과거 기록/노트 회수
  3. 웹 검색 → 최신 트렌드/뉴스 수집 (선택)
  4. LLM에 컨텍스트 전달 → 제안 생성
  5. 제안 저장 + 알림 발송 (Webhook/Telegram)
- **피드백 루프**:
  - 사용자가 👍/👎 → 제안 품질 학습
  - 승인/거절 비율로 제안 전략 자동 조정

### 5. Memory Store (Qdrant)
- **Port**: 6333
- **컬렉션**:
  - `conversations` — 대화 청크
  - `documents` — 노트/문서 청크
  - `bookmarks` — 북마크 청크
- **임베딩 차원**: 프로바이더에 따라 자동 설정

### 6. LLM Router (`shared/llm_router.py`)
- **역할**: 멀티 프로바이더 추상화
- **지원 프로바이더**:
  - OpenAI (GPT-4o, text-embedding-3-small)
  - Anthropic (Claude Sonnet/Opus)
  - Google (Gemini Pro/Flash)
  - Ollama (로컬 모델, 무료)
- **인터페이스**:
  ```python
  router = LLMRouter(provider="openai", api_key="sk-xxx")
  response = await router.chat(messages=[...])
  embedding = await router.embed("텍스트")
  ```
- **Fallback**: 1차 프로바이더 실패 시 2차로 자동 전환

### 7. Frontend (`frontend/`)
- **Port**: 3080
- **Tech**: nginx + vanilla HTML/JS (경량)
- **페이지**:
  - `/` — 대시보드 (오늘의 제안 + 프로필 요약)
  - `/search` — 메모리 검색
  - `/profile` — 관심사/패턴 상세
  - `/history` — 제안 이력 + 피드백
  - `/settings` — 프로바이더/스케줄 설정

---

## Database Schema (PostgreSQL)

```sql
-- 사용자 프로필
CREATE TABLE user_profile (
    id SERIAL PRIMARY KEY,
    profile_data JSONB NOT NULL,    -- 관심사, 패턴, 성향
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 관심사
CREATE TABLE interests (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(200) NOT NULL,
    category VARCHAR(100),          -- tech, business, personal
    intensity FLOAT DEFAULT 0,      -- 0~1 관심 강도
    mention_count INT DEFAULT 0,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    trend VARCHAR(20) DEFAULT 'stable', -- rising, falling, stable, new
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 제안
CREATE TABLE suggestions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    related_interests INT[],        -- interests.id 참조
    source_context TEXT,            -- RAG에서 가져온 근거
    feedback VARCHAR(20),           -- good, bad, neutral, null
    feedback_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 의사결정 이력
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500),
    decision VARCHAR(50),           -- approved, rejected, deferred
    context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 수집 로그
CREATE TABLE ingest_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100),            -- conversation, obsidian, bookmark
    item_count INT,
    vector_count INT,
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Configuration (.env)

```bash
# === LLM Provider (필수) ===
LLM_PROVIDER=openai                 # openai | anthropic | google | ollama
LLM_API_KEY=sk-xxx                  # 프로바이더 API 키
LLM_MODEL=gpt-4o-mini              # 채팅 모델
EMBEDDING_PROVIDER=openai           # 임베딩 프로바이더 (LLM과 다를 수 있음)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536                  # 모델별 자동 설정

# === Fallback (선택) ===
LLM_FALLBACK_PROVIDER=              # 장애 시 대체
LLM_FALLBACK_API_KEY=
LLM_FALLBACK_MODEL=

# === Schedule ===
PROFILER_CRON=0 0 * * *             # 매일 자정
ADVISOR_CRON=0 8 * * *              # 매일 아침 8시
ADVISOR_TIMEZONE=Asia/Seoul

# === Notification (선택) ===
NOTIFY_WEBHOOK=                     # Webhook URL
TELEGRAM_BOT_TOKEN=                 # Telegram 알림
TELEGRAM_CHAT_ID=

# === Data Sources (선택) ===
OBSIDIAN_VAULT_PATH=                # Obsidian vault 경로
BOOKMARK_API_URL=                   # Karakeep/Raindrop API
BOOKMARK_API_KEY=

# === System ===
POSTGRES_PASSWORD=change_me_please
LOG_LEVEL=INFO
```

---

## MVP Scope (Day 1)

### Must Have
- [ ] LLM Router (OpenAI + Anthropic + Google)
- [ ] Ingest: 대화 로그 수집 + 벡터화
- [ ] Profiler: 관심사 추출 (최근 7일)
- [ ] Advisor: 일일 제안 생성
- [ ] API Gateway: 핵심 엔드포인트
- [ ] Frontend: 대시보드 + 검색
- [ ] Docker Compose: 원클릭 배포
- [ ] README: 설치 + 사용 가이드

### Nice to Have (v1.1)
- [ ] Obsidian vault 수집
- [ ] 북마크 동기화
- [ ] Webhook 알림
- [ ] 피드백 학습 루프
- [ ] Ollama 로컬 모델 지원

### Future (v2.0)
- [ ] 멀티 유저 지원
- [ ] 플러그인 시스템 (커스텀 소스)
- [ ] 관심사 네트워크 시각화
- [ ] 자동 리서치 에이전트
