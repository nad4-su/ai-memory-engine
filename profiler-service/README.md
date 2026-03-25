# Profiler Service

사용자 대화/활동을 분석하여 프로필을 자동 갱신하는 서비스.

## Features

- **대화 분석**: LLM을 활용한 대화/활동 기록 분석
- **관심사 추적**: 관심사 강도 계산 (mention frequency × recency weighting)
- **트렌드 감지**: 이번 주 vs 지난 주 비교로 rising/falling/stable/new 분류
- **행동 패턴**: 활동 시간대, 요일별 패턴, 의사결정 스타일 감지
- **자동 스케줄링**: APScheduler로 주기적 분석 (기본: 매일 자정)

## Architecture

```
profiler-service/
├── main.py              — FastAPI + APScheduler
├── analyzer.py          — LLM 기반 대화 분석
├── interest_tracker.py  — 관심사 강도 및 트렌드 계산
├── pattern_detector.py  — 행동 패턴 감지
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### `POST /api/v1/profiler/analyze`

수동으로 프로필 분석 트리거.

**Request:**
```json
{
  "user_id": "default",
  "days": 7
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": "default",
  "result": {
    "interests": [...],
    "patterns": {...},
    "trends": [...]
  }
}
```

### `GET /api/v1/profiler/status`

마지막 분석 상태 조회.

**Response:**
```json
{
  "status": "ok",
  "last_analysis": {
    "last_run": "2025-03-26T03:00:00",
    "status": "success",
    "message": "Analysis completed successfully"
  },
  "scheduler": {
    "running": true,
    "cron": "0 0 * * *"
  }
}
```

### `GET /health`

Health check.

## Configuration

`.env` 파일 또는 환경변수로 설정:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | (required) |
| `QDRANT_URL` | Qdrant server URL | `http://qdrant:6333` |
| `LLM_PROVIDER` | LLM provider (openai/anthropic/google/ollama) | (required) |
| `LLM_API_KEY` | LLM API key | (required) |
| `LLM_MODEL` | LLM model name | `gpt-4o-mini` |
| `PROFILER_CRON` | Cron schedule | `0 0 * * *` |
| `DEFAULT_USER_ID` | Default user ID | `default` |
| `PORT` | Server port | `8002` |

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run service
python main.py
```

## Docker

```bash
# Build
docker build -t profiler-service .

# Run
docker run -p 8002:8002 --env-file .env profiler-service
```

## Integration

다른 서비스와의 통합:

1. **Ingest Service**: 대화/문서 수집 → PostgreSQL `ingest_log` 테이블
2. **Profiler Service**: 주기적으로 분석 → `user_profile`, `interests` 테이블 갱신
3. **Advisor Service**: 프로필 기반 제안 생성

## Algorithm Details

### 관심사 강도 계산

```
intensity = (mention_count × recency_weight) / max_value
recency_weight = 0.9 ^ days_ago
```

- 오늘: 1.0
- 1일 전: 0.9
- 2일 전: 0.81
- 7일 전: ~0.3

### 트렌드 분류

- **new**: 지난주 0회, 이번주 > 0회
- **rising**: 이번주 > 지난주 × 1.5
- **falling**: 이번주 < 지난주 × 0.5
- **stable**: 그 외

## Database Schema

### `user_profile`
```sql
CREATE TABLE user_profile (
    user_id TEXT PRIMARY KEY,
    profile_data JSONB,
    updated_at TIMESTAMP
);
```

### `interests`
```sql
CREATE TABLE interests (
    user_id TEXT,
    topic TEXT,
    category TEXT,
    intensity NUMERIC,
    evidence TEXT,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, topic)
);
```

## Logging

로그 레벨: `INFO`

주요 로그:
- 분석 시작/완료
- LLM 호출 결과
- 저장된 관심사 수
- 에러 및 경고
