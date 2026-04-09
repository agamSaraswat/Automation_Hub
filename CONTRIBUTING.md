# Contributing to Agam Automation Hub

## For Soumyabrata (Collaborator)

Welcome! This document covers everything you need to contribute effectively.

### Quick Start

```bash
git clone https://github.com/agamsaraswat/agam-automation-hub.git
cd agam-automation-hub
bash scripts/setup.sh          # or: make setup
cp .env.example .env           # fill in your API keys
make web                       # start backend + frontend
```

### Workflow

1. **Never push directly to `main`** — it's branch-protected.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Write code + tests. All new features need tests in `tests/`.
4. Push your branch: `git push origin feature/your-feature-name`
5. Open a Pull Request → Agam reviews and merges.

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/...` | `feature/slack-notifications` |
| Bug fix | `fix/...` | `fix/email-triage-crash` |
| Agent | `agent/...` | `agent/linkedin-scheduler` |
| Docs | `docs/...` | `docs/update-setup-guide` |

### Code Standards

- All Python: formatted with `ruff` (`make lint`)
- All new modules: docstring at the top
- All new features: at least one test in `tests/`
- No hardcoded personal info (names, emails, phone numbers) — use `ProfileManager`
- No API keys in source — always use `.env`

### Architecture

```
src/
├── agent/          Claude client wrapper (use this for all LLM calls)
├── jobs/           Job discovery, resume tailoring, tracking
├── linkedin/       LinkedIn content generation + publishing
├── messaging/      Gmail, Telegram, Discord bots
├── briefing/       Morning briefing generator
├── scheduler/      Cron job orchestration
├── services/       Shared services (automation, token tracking, settings)
└── web/            FastAPI backend + routers
```

**Key pattern: Adversarial Harness** (`src/jobs/harness.py`)
All AI-generated content goes through: Planner → Generator → Evaluator.
New agent features should follow this pattern.

### Adding a New Agent

1. Create `src/your_module/your_agent.py`
2. Use `ClaudeClient` from `src.agent.claude_client`
3. Use `ProfileManager` from `src.config.profile_manager` (never hardcode user data)
4. Add a router in `src/web/routers/` if it needs an API endpoint
5. Register in `src/web/main.py`
6. Add tests in `tests/test_your_module.py`
7. Open a PR

### Running Tests

```bash
make test
# or: pytest tests/ -v
```

### Questions?

Check `docs/COLLABORATION_FRAMEWORK.md` for the full workflow guide.
