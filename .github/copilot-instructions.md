# 노션우렁각시 (woongaksi)

Background relay daemon that bridges Notion and AI agents via Telegram. Polls Notion DBs, detects changes, sends to Telegram — so AI agents know Notion state from chat context without expensive API calls.

**Core principle: ZERO LLM token cost.** Pure HTTP only. Never add LLM calls.

## Why
- AI agents waste tokens calling Notion API (tool use + parsing) every question
- They store results in memory → stale data → wrong answers
- Woongaksi: poll Notion (free) → relay changes to Telegram → AI reads chat context → no API needed

## Architecture
`__main__.py` → config → APScheduler loop → per DB: `client.py` (query) → `differ.py` (diff) → `formatter.py` (HTML) → `telegram.py` (send)

## Files
- `config.py`: `Config` dataclass, YAML + env loader
- `client.py`: Generic Notion query, 14 property types, pagination
- `differ.py`: `DiffResult` (.added/.removed/.modified), JSON cache
- `formatter.py`: DiffResult → Telegram HTML
- `telegram.py`: Send with retry, auto-split >4096 chars
- `scheduler.py`: APScheduler orchestrator

## Rules
- Secrets in env vars only (NOTION_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- DB definitions in `config.yaml`
- Relative imports only (`from .config import ...`)
- Python >=3.10, deps: requests, apscheduler <4, pyyaml
- HTML escape all user data via `_escape_html()`
- Never add LLM/AI calls to this codebase

## AI integration
- Woongaksi and AI agent share the same Telegram chat
- AI treats relay messages (📋/📊 prefix) as real-time Notion data
- AI should not re-query Notion for recently relayed data
