# 🧠 AI Memory Engine

**Your personal AI that learns from everything you read, write, and interact with.**

> 🇰🇷 [한국어 README](README.ko.md)

AI Memory Engine is a self-hosted, privacy-first intelligent memory system that ingests your conversations, documents, and bookmarks, builds a deep understanding of your interests and patterns, and proactively suggests personalized insights every day.

---

## ✨ Features

- **🔍 Semantic Search**: Find relevant memories across all your data using natural language
- **👤 Intelligent Profiling**: Automatically learns your interests, behavior patterns, and decision style
- **💡 Daily Suggestions**: Personalized recommendations based on your profile (learning, productivity, wellness)
- **📊 Beautiful Dashboard**: Modern dark-themed UI with real-time insights
- **🔌 Multi-Provider LLM**: Support for OpenAI, Anthropic, Google, and Ollama (with fallback)
- **🐳 One-Command Deployment**: Fully containerized with Docker Compose
- **🔒 Privacy-First**: Self-hosted, no data leaves your infrastructure

---

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/nad4-su/ai-memory-engine.git
cd ai-memory-engine

# 2. Configure environment
cp .env.example .env
# Edit .env with your LLM API key

# 3. Launch all services
docker compose up -d
```

**That's it!** Open http://localhost:3080 to access the dashboard.

---

## 📐 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│ API Gateway  │────▶│  PostgreSQL │
│   (Nginx)   │     │   (FastAPI)  │     │   (Metadata)│
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├───────────────┐
                           ▼               ▼
                    ┌──────────────┐  ┌──────────┐
                    │ Ingest Service│  │  Qdrant  │
                    │ (Data Import) │  │ (Vectors)│
                    └──────────────┘  └──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Profiler    │  │   Advisor    │  │ LLM Router   │
│ (Analysis)   │  │ (Suggestions)│  │ (Multi-LLM)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Services:**

- **Frontend**: React-style dashboard (HTML/CSS/JS + Nginx)
- **API Gateway**: Central REST API (FastAPI)
- **Ingest Service**: Imports data from Obsidian, bookmarks, conversations
- **Profiler Service**: Analyzes interests and patterns (scheduled)
- **Advisor Service**: Generates personalized suggestions (scheduled)
- **PostgreSQL**: Stores metadata, profiles, suggestions
- **Qdrant**: Vector database for semantic search

See [Architecture Documentation](docs/ARCHITECTURE.md) for details.

---

## 🔧 Configuration

### LLM Providers

Set in `.env`:

| Provider   | Required Keys                     | Models                          |
|------------|-----------------------------------|---------------------------------|
| OpenAI     | `LLM_API_KEY`                     | `gpt-4o-mini`, `gpt-4`, `o1`    |
| Anthropic  | `LLM_API_KEY`                     | `claude-sonnet-4-20250514`      |
| Google     | `LLM_API_KEY`                     | `gemini-2.0-flash-exp`          |
| Ollama     | (none, uses `http://localhost:11434`) | `llama3`, `mistral`, etc.   |

**Example:**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4o-mini
```

**Fallback (optional):**
```bash
LLM_FALLBACK_PROVIDER=anthropic
LLM_FALLBACK_API_KEY=sk-ant-xxx
LLM_FALLBACK_MODEL=claude-sonnet-4-20250514
```

### Data Sources

**Obsidian Vault:**
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
```

**Bookmarks (Raindrop.io, Linkding, etc.):**
```bash
BOOKMARK_API_URL=https://api.raindrop.io/rest/v1/raindrops/0
BOOKMARK_API_KEY=your-api-key
```

### Schedule

Uses cron syntax:

```bash
PROFILER_CRON=0 0 * * *   # Daily at midnight (analyze interests)
ADVISOR_CRON=0 8 * * *    # Daily at 8 AM (generate suggestions)
```

---

## 📡 API Documentation

### Endpoints

**Health:**
- `GET /api/v1/health` - Service health check
- `GET /api/v1/status` - System status

**Ingest:**
- `POST /api/v1/ingest/conversation` - Ingest conversation
- `POST /api/v1/ingest/document` - Ingest document
- `POST /api/v1/ingest/bookmark` - Ingest bookmark
- `POST /api/v1/ingest/trigger` - Manually trigger data collection

**Search:**
- `GET /api/v1/search?query=...&source=...` - Semantic search

**Profile:**
- `GET /api/v1/profile` - Get user profile
- `GET /api/v1/profile/interests` - Get interests
- `GET /api/v1/profile/patterns` - Get behavior patterns
- `POST /api/v1/profile/trigger` - Manually run profiling

**Suggestions:**
- `GET /api/v1/suggestions` - Get latest suggestions
- `GET /api/v1/suggestions/{id}` - Get suggestion details
- `POST /api/v1/suggestions/{id}/feedback` - Submit feedback (👍/👎)
- `GET /api/v1/suggestions/history` - Get suggestion history

See [API Documentation](docs/API.md) for full details.

---

## 🎨 Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)
*Real-time system status, today's suggestions, and top interests*

### Search
![Search](docs/screenshots/search.png)
*Semantic search across all your memories*

### Profile
![Profile](docs/screenshots/profile.png)
*Interests, behavior patterns, and decision style*

---

## 🛠️ Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run PostgreSQL and Qdrant
docker compose up -d postgres qdrant

# Set environment variables
export DATABASE_URL="postgresql://memory_user:password@localhost:5433/memory_engine"
export QDRANT_URL="http://localhost:6334"

# Run services
python api-gateway/main.py
python ingest-service/main.py
python profiler-service/main.py
python advisor-service/main.py

# Serve frontend
cd frontend && python -m http.server 3080
```

### Project Structure

```
ai-memory-engine/
├── api-gateway/          # Central REST API
├── ingest-service/       # Data import service
├── profiler-service/     # Interest analysis
├── advisor-service/      # Suggestion generation
├── frontend/             # Web UI (HTML/CSS/JS)
├── shared/               # Shared modules (LLM router)
├── db/                   # Database schemas
├── docs/                 # Documentation
├── docker-compose.yml    # Service orchestration
└── .env.example          # Configuration template
```

---

## 🗺️ Roadmap

- [x] Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama)
- [x] Semantic search with Qdrant
- [x] Interest profiling and pattern analysis
- [x] Daily suggestion generation
- [x] Feedback loop (👍/👎)
- [ ] Multi-user support with authentication
- [ ] Mobile app (React Native)
- [ ] Browser extension for web scraping
- [ ] Slack/Discord integration
- [ ] Advanced analytics (graphs, trends)
- [ ] Export/import functionality

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Development Guidelines:**
- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation
- Keep commits atomic and well-described

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vector search powered by [Qdrant](https://qdrant.tech/)
- UI inspired by modern dashboard designs
- LLM routing concept from [LiteLLM](https://github.com/BerriAI/litellm)

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/nad4-su/ai-memory-engine/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nad4-su/ai-memory-engine/discussions)
- **Email**: support@example.com

---

**Made with ❤️ by the AI Memory Engine team**
