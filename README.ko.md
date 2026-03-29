# 🧠 AI Memory Engine

**당신이 읽고, 쓰고, 상호작용하는 모든 것을 학습하는 개인 AI**

AI Memory Engine은 자체 호스팅 가능한 프라이버시 우선 지능형 메모리 시스템입니다. 대화, 문서, 북마크를 수집하여 당신의 관심사와 패턴을 깊이 이해하고, 매일 개인화된 통찰을 능동적으로 제안합니다.

---

## ✨ 주요 기능

- **🔍 시맨틱 검색**: 자연어로 모든 데이터에서 관련 기억을 검색
- **👤 지능형 프로파일링**: 관심사, 행동 패턴, 의사결정 스타일 자동 학습
- **💡 일일 제안**: 프로필 기반 개인화 추천 (학습, 생산성, 웰니스)
- **📊 아름다운 대시보드**: 실시간 인사이트를 제공하는 현대적인 다크 테마 UI
- **🔌 멀티 프로바이더 LLM**: OpenAI, Anthropic, Google, Ollama 지원 (폴백 기능 포함)
- **🐳 원클릭 배포**: Docker Compose로 완전히 컨테이너화
- **🔒 프라이버시 우선**: 자체 호스팅, 데이터가 외부로 유출되지 않음

---

## 🚀 빠른 시작 (5분)

```bash
# 1. 저장소 클론
git clone https://github.com/nad4-su/ai-memory-engine.git
cd ai-memory-engine

# 2. 환경 설정
cp .env.example .env
# .env 파일에 LLM API 키 입력

# 3. 모든 서비스 시작
docker compose up -d
```

**끝입니다!** http://localhost:3080 에서 대시보드에 접속하세요.

---

## 📐 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   프론트엔드 │────▶│ API 게이트웨이│────▶│ PostgreSQL  │
│   (Nginx)   │     │   (FastAPI)  │     │  (메타데이터)│
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├───────────────┐
                           ▼               ▼
                    ┌──────────────┐  ┌──────────┐
                    │  수집 서비스  │  │  Qdrant  │
                    │ (데이터 임포트)│  │  (벡터)  │
                    └──────────────┘  └──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  프로파일러  │  │   어드바이저  │  │ LLM 라우터   │
│   (분석)     │  │   (제안)     │  │ (멀티 LLM)   │
└──────────────┘  └──────────────┘  └──────────────┘
```

**서비스:**

- **프론트엔드**: React 스타일 대시보드 (HTML/CSS/JS + Nginx)
- **API 게이트웨이**: 중앙 REST API (FastAPI)
- **수집 서비스**: Obsidian, 북마크, 대화에서 데이터 임포트
- **프로파일러 서비스**: 관심사와 패턴 분석 (스케줄)
- **어드바이저 서비스**: 개인화 제안 생성 (스케줄)
- **PostgreSQL**: 메타데이터, 프로필, 제안 저장
- **Qdrant**: 시맨틱 검색을 위한 벡터 데이터베이스

자세한 내용은 [아키텍처 문서](docs/ARCHITECTURE.md)를 참조하세요.

---

## 🔧 설정

### LLM 프로바이더

`.env` 파일에서 설정:

| 프로바이더 | 필수 키                           | 모델                            |
|-----------|-----------------------------------|---------------------------------|
| OpenAI    | `LLM_API_KEY`                     | `gpt-4o-mini`, `gpt-4`, `o1`    |
| Anthropic | `LLM_API_KEY`                     | `claude-sonnet-4-20250514`      |
| Google    | `LLM_API_KEY`                     | `gemini-2.0-flash-exp`          |
| Ollama    | (불필요, `http://localhost:11434` 사용) | `llama3`, `mistral` 등     |

**예시:**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4o-mini
```

**폴백 (선택사항):**
```bash
LLM_FALLBACK_PROVIDER=anthropic
LLM_FALLBACK_API_KEY=sk-ant-xxx
LLM_FALLBACK_MODEL=claude-sonnet-4-20250514
```

### 데이터 소스

**Obsidian Vault:**
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
```

**북마크 (Raindrop.io, Linkding 등):**
```bash
BOOKMARK_API_URL=https://api.raindrop.io/rest/v1/raindrops/0
BOOKMARK_API_KEY=your-api-key
```

### 스케줄

Cron 문법 사용:

```bash
PROFILER_CRON=0 0 * * *   # 매일 자정 (관심사 분석)
ADVISOR_CRON=0 8 * * *    # 매일 오전 8시 (제안 생성)
```

---

## 📡 API 문서

### 엔드포인트

**헬스체크:**
- `GET /api/v1/health` - 서비스 헬스체크
- `GET /api/v1/status` - 시스템 상태

**수집:**
- `POST /api/v1/ingest/conversation` - 대화 수집
- `POST /api/v1/ingest/document` - 문서 수집
- `POST /api/v1/ingest/bookmark` - 북마크 수집
- `POST /api/v1/ingest/trigger` - 수동으로 데이터 수집 트리거

**검색:**
- `GET /api/v1/search?query=...&source=...` - 시맨틱 검색

**프로필:**
- `GET /api/v1/profile` - 사용자 프로필 조회
- `GET /api/v1/profile/interests` - 관심사 조회
- `GET /api/v1/profile/patterns` - 행동 패턴 조회
- `POST /api/v1/profile/trigger` - 수동으로 프로파일링 실행

**제안:**
- `GET /api/v1/suggestions` - 최신 제안 조회
- `GET /api/v1/suggestions/{id}` - 제안 상세 조회
- `POST /api/v1/suggestions/{id}/feedback` - 피드백 제출 (👍/👎)
- `GET /api/v1/suggestions/history` - 제안 히스토리 조회

전체 상세 내용은 [API 문서](docs/API.md)를 참조하세요.

---

## 🎨 스크린샷

### 대시보드
![대시보드](docs/screenshots/dashboard.png)
*실시간 시스템 상태, 오늘의 제안, 주요 관심사*

### 검색
![검색](docs/screenshots/search.png)
*모든 메모리에서 시맨틱 검색*

### 프로필
![프로필](docs/screenshots/profile.png)
*관심사, 행동 패턴, 의사결정 스타일*

---

## 🛠️ 개발

### 로컬 개발 (Docker 없이)

```bash
# 의존성 설치
pip install -r requirements.txt

# PostgreSQL과 Qdrant 실행
docker compose up -d postgres qdrant

# 환경 변수 설정
export DATABASE_URL="postgresql://memory_user:password@localhost:5433/memory_engine"
export QDRANT_URL="http://localhost:6334"

# 서비스 실행
python api-gateway/main.py
python ingest-service/main.py
python profiler-service/main.py
python advisor-service/main.py

# 프론트엔드 서빙
cd frontend && python -m http.server 3080
```

### 프로젝트 구조

```
ai-memory-engine/
├── api-gateway/          # 중앙 REST API
├── ingest-service/       # 데이터 임포트 서비스
├── profiler-service/     # 관심사 분석
├── advisor-service/      # 제안 생성
├── frontend/             # 웹 UI (HTML/CSS/JS)
├── shared/               # 공유 모듈 (LLM 라우터)
├── db/                   # 데이터베이스 스키마
├── docs/                 # 문서
├── docker-compose.yml    # 서비스 오케스트레이션
└── .env.example          # 설정 템플릿
```

---

## 🗺️ 로드맵

- [x] 멀티 프로바이더 LLM 지원 (OpenAI, Anthropic, Google, Ollama)
- [x] Qdrant를 사용한 시맨틱 검색
- [x] 관심사 프로파일링 및 패턴 분석
- [x] 일일 제안 생성
- [x] 피드백 루프 (👍/👎)
- [ ] 인증 기능이 있는 멀티 사용자 지원
- [ ] 모바일 앱 (React Native)
- [ ] 웹 스크래핑을 위한 브라우저 확장
- [ ] Slack/Discord 통합
- [ ] 고급 분석 (그래프, 트렌드)
- [ ] 내보내기/가져오기 기능

---

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

---

## 🤝 기여하기

기여를 환영합니다! 다음 절차를 따라주세요:

1. 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경 사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 엽니다

**개발 가이드라인:**
- Python 코드는 PEP 8을 따릅니다
- 새로운 기능에 대한 테스트를 추가합니다
- 문서를 업데이트합니다
- 커밋을 원자적이고 명확하게 작성합니다

---

## 🙏 감사의 말

- [FastAPI](https://fastapi.tiangolo.com/)로 구축
- [Qdrant](https://qdrant.tech/)로 구동되는 벡터 검색
- 현대적인 대시보드 디자인에서 영감을 받은 UI
- [LiteLLM](https://github.com/BerriAI/litellm)의 LLM 라우팅 개념 참조

---

## 📧 지원

- **이슈**: [GitHub Issues](https://github.com/nad4-su/ai-memory-engine/issues)
- **토론**: [GitHub Discussions](https://github.com/nad4-su/ai-memory-engine/discussions)
- **이메일**: support@example.com

---

**AI Memory Engine 팀이 ❤️ 를 담아 제작했습니다**
