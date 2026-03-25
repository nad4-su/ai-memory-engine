# AI Memory Engine — Services Overview

프로젝트 전체 서비스 구성 및 통합 가이드.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  API Gateway (8000)                 │
│          /api/ingest, /api/profiler, /api/advisor   │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Ingest   │ │ Profiler │ │ Advisor  │
  │ Service  │ │ Service  │ │ Service  │
  │  (8001)  │ │  (8002)  │ │  (8003)  │
  └────┬─────┘ └────┬─────┘ └────┬─────┘
       │            │            │
       └────────────┼────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
  ┌──────────┐            ┌──────────┐
  │PostgreSQL│            │ Qdrant   │
  │  (5432)  │            │  (6333)  │
  └──────────┘            └──────────┘
```

## Services

### 1. Ingest Service (8001)
**기능**: 대화/문서 수집 및 저장
- REST API로 데이터 수집
- PostgreSQL에 원본 저장
- Qdrant에 벡터 임베딩 저장

**엔드포인트**:
- `POST /api/v1/ingest` — 데이터 수집
- `GET /health` — Health check

### 2. Profiler Service (8002)
**기능**: 사용자 프로필 분석
- LLM 기반 대화/활동 분석
- 관심사 추적 및 트렌드 감지
- 행동 패턴 감지
- 자동 스케줄링 (기본: 매일 자정)

**엔드포인트**:
- `POST /api/v1/profiler/analyze` — 수동 분석 트리거
- `GET /api/v1/profiler/status` — 분석 상태 조회
- `GET /health` — Health check

### 3. Advisor Service (8003)
**기능**: 선제 제안 생성
- LLM 기반 실행 가능한 제안 생성
- RAG 검색으로 컨텍스트 강화
- 웹 검색 (선택)
- Webhook/Telegram 알림
- 자동 스케줄링 (기본: 매일 08:00)

**엔드포인트**:
- `POST /api/v1/advisor/generate` — 수동 생성 트리거
- `GET /api/v1/advisor/status` — 생성 상태 조회
- `GET /health` — Health check

### 4. API Gateway (8000)
**기능**: 통합 진입점
- 모든 서비스 라우팅
- CORS, 인증 (선택)
- Rate limiting (선택)

**엔드포인트**:
- `/api/ingest/*` → Ingest Service
- `/api/profiler/*` → Profiler Service
- `/api/advisor/*` → Advisor Service

## Data Flow

### 1. 수집 플로우
```
사용자 입력 → API Gateway → Ingest Service
                                  ├─→ PostgreSQL (ingest_log)
                                  └─→ Qdrant (벡터 임베딩)
```

### 2. 분석 플로우
```
Profiler (스케줄)
  ├─→ PostgreSQL에서 최근 7일 데이터 조회
  ├─→ Qdrant에서 대화 청크 조회
  ├─→ LLM 분석 (interests, patterns, trends)
  └─→ PostgreSQL에 저장 (user_profile, interests)
```

### 3. 제안 플로우
```
Advisor (스케줄)
  ├─→ PostgreSQL에서 프로필 + 관심사 조회
  ├─→ Qdrant RAG 검색 (관심사별 관련 기록)
  ├─→ (선택) DuckDuckGo 웹 검색
  ├─→ LLM 제안 생성
  ├─→ PostgreSQL에 저장 (suggestions)
  └─→ 알림 발송 (Webhook/Telegram)
```

## Database Schema

### PostgreSQL Tables

```sql
-- 수집 로그
CREATE TABLE ingest_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 사용자 프로필
CREATE TABLE user_profile (
    user_id TEXT PRIMARY KEY,
    profile_data JSONB,
    updated_at TIMESTAMP
);

-- 관심사
CREATE TABLE interests (
    user_id TEXT,
    topic TEXT,
    category TEXT,
    intensity NUMERIC,
    evidence TEXT,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, topic)
);

-- 제안
CREATE TABLE suggestions (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    content TEXT,
    category TEXT,
    actionable_steps JSONB,
    related_interest TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 의사결정 (선택)
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    decision_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Qdrant Collection

```
memory_chunks
  ├─ vector: embedding (1536-dim for OpenAI)
  └─ payload:
       ├─ user_id
       ├─ text
       ├─ metadata
       └─ timestamp
```

## Environment Variables

각 서비스별 `.env` 파일 참고:

- `profiler-service/.env.example`
- `advisor-service/.env.example`
- `ingest-service/.env.example`
- `api-gateway/.env.example`

## Deployment

### Docker Compose (권장)

```bash
# 전체 스택 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d profiler-service advisor-service
```

### Individual Services

```bash
# Profiler Service
cd profiler-service
pip install -r requirements.txt
python main.py

# Advisor Service
cd advisor-service
pip install -r requirements.txt
python main.py
```

## Testing

```bash
# Health check 테스트
./test_services.sh

# Manual API test
curl http://localhost:8002/health
curl http://localhost:8003/health

# Trigger analysis
curl -X POST http://localhost:8002/api/v1/profiler/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id": "default", "days": 7}'

# Trigger suggestion
curl -X POST http://localhost:8003/api/v1/advisor/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "default", "web_research": false, "notify": false}'
```

## Cost Optimization

LLM 비용 절감 전략:

1. **모델 선택**: `gpt-4o-mini` or `gemini-2.0-flash`
2. **토큰 제한**: 
   - Profiler: `max_tokens=2000`
   - Advisor: `max_tokens=2500`
3. **데이터 제한**:
   - 최근 7일 데이터만 분석
   - RAG 결과: 관심사당 5건
   - 웹 검색: 키워드당 3건
4. **스케줄 조정**:
   - Profiler: 매일 자정 (필요시 주간으로 변경)
   - Advisor: 매일 08:00 (필요시 주간으로 변경)

## Monitoring

각 서비스 로그:

```bash
# Docker logs
docker logs -f profiler-service
docker logs -f advisor-service

# Status endpoints
curl http://localhost:8002/api/v1/profiler/status
curl http://localhost:8003/api/v1/advisor/status
```

## Troubleshooting

### 1. Database connection error
```bash
# Check PostgreSQL
docker ps | grep postgres
docker logs postgres

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### 2. Qdrant connection error
```bash
# Check Qdrant
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections
```

### 3. LLM API error
```bash
# Check API key
echo $LLM_API_KEY

# Test LLM provider
python -c "from shared.llm_router import LLMRouter; r = LLMRouter.from_env(); print(r.primary)"
```

### 4. Scheduler not running
```bash
# Check status endpoint
curl http://localhost:8002/api/v1/profiler/status | jq '.scheduler'

# Check logs for APScheduler
docker logs profiler-service | grep -i scheduler
```

## Next Steps

1. **API Gateway 통합**: Nginx/Traefik로 서비스 라우팅
2. **인증/인가**: JWT 토큰 기반 사용자 인증
3. **Rate Limiting**: Redis 기반 요청 제한
4. **모니터링**: Prometheus + Grafana 대시보드
5. **CI/CD**: GitHub Actions 자동 배포
