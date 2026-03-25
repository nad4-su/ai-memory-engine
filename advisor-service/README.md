# Advisor Service

사용자 프로필과 관심사를 기반으로 선제 제안을 생성하는 서비스.

## Features

- **제안 생성**: LLM 기반 실행 가능한 제안 생성 (actionable steps 포함)
- **RAG 검색**: Qdrant에서 과거 기록 검색하여 컨텍스트 강화
- **웹 검색**: DuckDuckGo로 최신 트렌드 검색 (선택)
- **알림 발송**: Webhook 또는 Telegram으로 제안 전달
- **자동 스케줄링**: APScheduler로 주기적 생성 (기본: 매일 08:00)

## Architecture

```
advisor-service/
├── main.py               — FastAPI + APScheduler
├── suggestion_engine.py  — LLM 기반 제안 생성
├── web_researcher.py     — DuckDuckGo 웹 검색
├── notifier.py           — Webhook/Telegram 알림
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### `POST /api/v1/advisor/generate`

수동으로 제안 생성 트리거.

**Request:**
```json
{
  "user_id": "default",
  "web_research": false,
  "notify": false
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": "default",
  "suggestions_count": 3,
  "suggestions": [
    {
      "title": "제안 제목",
      "content": "제안 내용",
      "category": "비즈니스",
      "actionable_steps": ["단계1", "단계2", "단계3"],
      "related_interest": "관련 관심사"
    }
  ]
}
```

### `GET /api/v1/advisor/status`

마지막 생성 상태 조회.

**Response:**
```json
{
  "status": "ok",
  "last_generation": {
    "last_run": "2025-03-26T08:00:00",
    "status": "success",
    "message": "Suggestions generated successfully",
    "suggestions_count": 3
  },
  "scheduler": {
    "running": true,
    "cron": "0 8 * * *",
    "timezone": "Asia/Seoul"
  },
  "features": {
    "web_research": false,
    "notifier": true
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
| `LLM_PROVIDER` | LLM provider | (required) |
| `LLM_API_KEY` | LLM API key | (required) |
| `LLM_MODEL` | LLM model name | `gpt-4o-mini` |
| `ADVISOR_CRON` | Cron schedule | `0 8 * * *` |
| `ADVISOR_TIMEZONE` | Timezone | `Asia/Seoul` |
| `WEB_RESEARCH_ENABLED` | Enable web search | `false` |
| `NOTIFY_WEBHOOK` | Webhook URL | (optional) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (optional) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | (optional) |
| `DEFAULT_USER_ID` | Default user ID | `default` |
| `PORT` | Server port | `8003` |

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
docker build -t advisor-service .

# Run
docker run -p 8003:8003 --env-file .env advisor-service
```

## Integration

다른 서비스와의 통합:

1. **Profiler Service**: 사용자 프로필 분석 → `user_profile`, `interests` 테이블
2. **Advisor Service**: 프로필 기반 제안 생성 → `suggestions` 테이블
3. **Notifier**: Webhook/Telegram으로 사용자에게 전달

## Suggestion Generation Flow

```
1. Fetch user profile + top interests (PostgreSQL)
2. RAG search: 각 관심사별 관련 과거 기록 (Qdrant)
3. (Optional) Web search: 최신 트렌드 (DuckDuckGo)
4. LLM call: 프로필 + RAG + 트렌드 → 제안 생성
5. Save to PostgreSQL `suggestions` table
6. Send notification (Webhook/Telegram)
```

## Notification Format

### Telegram Example

```
🔔 새로운 제안이 도착했습니다!

1. [비즈니스] AI 자동화 도구 도입 검토
   최근 관심사인 AI 개발과 자동화를 결합하여...
   실행 단계:
   • 현재 업무 프로세스 중 반복 작업 리스트업
   • AI 자동화 도구 벤치마킹 (Zapier, n8n 등)
   • POC 프로젝트 선정 및 테스트

2. [학습] 최신 AI 모델 트렌드 스터디
   ...
```

### Webhook Payload

```json
{
  "message": "formatted notification message",
  "suggestions": [...],
  "type": "advisor_suggestions"
}
```

## Database Schema

### `suggestions`
```sql
CREATE TABLE suggestions (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    content TEXT,
    category TEXT,
    actionable_steps JSONB,
    related_interest TEXT,
    created_at TIMESTAMP
);
```

## Web Research

DuckDuckGo 검색 (API 키 불필요):

- 최신 뉴스 검색 (`ddgs.news()`)
- 일반 텍스트 검색 (`ddgs.text()`)
- 관심사 키워드별 최대 3개 결과

활성화: `WEB_RESEARCH_ENABLED=true`

## Cost Optimization

LLM 비용 절감:

- 추천 모델: `gpt-4o-mini` or `gemini-2.0-flash`
- RAG 결과 제한: 관심사당 5건
- 웹 검색 결과 제한: 키워드당 3건
- 토큰 제한: `max_tokens=2500`

## Logging

로그 레벨: `INFO`

주요 로그:
- 제안 생성 시작/완료
- LLM 호출 결과
- 저장된 제안 수
- 알림 발송 결과
- 에러 및 경고
