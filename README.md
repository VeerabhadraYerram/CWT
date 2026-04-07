# CrowdWisdomTrading — Prediction Market AI Agent System

A **Hermes-inspired multi-agent framework** for researching, analyzing, and ranking traders across prediction markets (Polymarket & Kalshi). Features a closed learning loop, RAG-enhanced event enrichment via Apify, and an interactive chat interface.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         main.py (CLI)                            │
│  Rich tables · argparse (--limit, --category, --chat)            │
├──────────────────────────────────────────────────────────────────┤
│                     Orchestrator Pipeline                        │
│  1. Fetch Polymarket  ──►  2. Fetch Kalshi  ──►  3. Classify     │
│  4. Enrich (RAG)      ──►  5. Score & Rank  ──►  6. Persist      │
│  7. Learning Loop     ──►  8. Recommend                          │
├──────────────┬───────────┬──────────────┬────────────────────────┤
│  Agents      │  Tools    │  Memory      │  RAG                   │
│ ──────────── │ ───────── │ ──────────── │ ─────                  │
│ BaseAgent    │ LLMClient │ MemoryMgr    │ ContextStore (JSON)    │
│ Polymarket   │ Poly API  │ SkillsMgr    │ VectorStore (ChromaDB) │
│ Kalshi       │ Kalshi API│              │                        │
│ NicheMapper  │ Apify     │              │                        │
│ RAGEnrich    │ DataStore │              │                        │
│ LearningLoop │           │              │                        │
│ ChatAgent    │           │              │                        │
└──────────────┴───────────┴──────────────┴────────────────────────┘
```

## Technical Stack

| Component        | Technology                                        |
|------------------|---------------------------------------------------|
| Language         | Python 3.11+                                      |
| LLM Provider     | [OpenRouter](https://openrouter.ai/) (free tier)  |
| Framework        | Hermes Agent patterns (skills, memory, learning)  |
| APIs             | Polymarket CLOB API, Kalshi Trade API v2           |
| Web Scraping     | [Apify](https://apify.com/) (free tier)           |
| Persistence      | SQLite (via `aiosqlite`)                           |
| CLI Output       | [Rich](https://github.com/Textualize/rich)        |
| HTTP             | `httpx` (async) + `tenacity` (retries)            |
| Logging          | `structlog` (structured JSON)                     |

## Key Features

### Multi-Platform Discovery
- **Polymarket**: Fetches real leaderboard data (PnL, volume, wallet addresses)
- **Kalshi**: Fetches live market data via v2 API (volume, event categorization)

### Hermes-Inspired Agent Framework
Implements core patterns from the [Hermes Agent](https://github.com/nousresearch/hermes-agent) framework:

- **Skill Extraction**: After each run, the learning loop agent extracts reusable heuristics as markdown skill files
- **Persistent Memory**: JSON-backed memory system with keyword search and session summarization
- **Closed Learning Loop**: Experience → Skill → Memory → Trust Update → Self-Assessment
- **Context-Aware Agents**: Skills and memories are automatically injected into agent prompts

### Niche Classification
Maps every trader/market into categories:
`POLITICS` · `SPORTS/NBA` · `SPORTS/NFL` · `SPORTS/MLB` · `WEATHER` · `ECONOMICS` · `CRYPTO` · `ENTERTAINMENT` · `SCIENCE/TECH` · `GENERAL`

Uses a two-tier approach:
1. **Fast keyword matching** for common patterns
2. **LLM classification** for descriptive market titles

### RAG Event Enrichment
Uses Apify to scrape web content for top events, stored in a JSON context store for retrieval during chat.

### Composite Scoring Engine
Multi-factor scoring formula (0-100):
- Win Rate (30%) · ROI (25%) · Recency (20%) · Trade Frequency (15%) · Volatility Penalty (10%)

## Quick Start

### 1. Clone & Install

```bash
git clone <this-repo>
cd CWT_Predictions_Market_Internship_Task

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   OPENROUTER_API_KEY=your_key  (required)
#   APIFY_API_TOKEN=your_token   (optional, for RAG)
```

### 3. Run

```bash
# Default run (top 10 traders)
python main.py

# Custom limit and category
python main.py --limit 20 --category POLITICS

# Interactive chat mode
python main.py --chat
```

## Project Structure

```
├── main.py                       # CLI entry point (Rich output)
├── config/
│   └── settings.py               # Central configuration (env vars)
├── agents/
│   ├── base_agent.py             # Hermes-inspired base (skills + memory)
│   ├── orchestrator.py           # 8-step pipeline coordinator
│   ├── polymarket_agent.py       # Polymarket leaderboard fetcher
│   ├── kalshi_agent.py           # Kalshi v2 market fetcher
│   ├── niche_agent.py            # LLM + keyword niche classifier
│   ├── rag_enrichment_agent.py   # Apify RAG enrichment
│   ├── learning_loop_agent.py    # Closed learning loop
│   └── chat_agent.py             # Recommendation generator
├── tools/
│   ├── llm_client.py             # OpenRouter SDK wrapper
│   ├── polymarket_api.py         # Polymarket CLOB API client
│   ├── kalshi_api.py             # Kalshi Trade API v2 client
│   ├── apify_scraper.py          # Apify web scraper
│   └── data_store.py             # SQLite persistence
├── models/
│   └── trader.py                 # TraderProfile data model
├── scoring/
│   └── scorer.py                 # Composite scoring engine
├── memory/
│   ├── memory_manager.py         # Persistent memory (JSON)
│   └── skills_manager.py         # Skill files (Markdown + YAML)
├── rag/
│   ├── context_store.py          # JSON-based RAG store
│   └── vector_store.py           # ChromaDB vector store (optional)
├── tests/
│   ├── test_scoring.py           # Scoring engine tests
│   ├── test_agents.py            # Agent & memory tests
│   ├── test_polymarket_api.py    # Polymarket API tests
│   └── test_kalshi_api.py        # Kalshi API tests
├── examples/
│   └── sample_input_output.md    # Real run transcripts
├── data/                         # Generated at runtime
│   ├── predictions.db            # SQLite database
│   └── context_store.json        # RAG context cache
├── memory/store/                 # Generated at runtime
│   ├── memory.json               # Persistent memories
│   └── skills/                   # Extracted skill files
├── requirements.txt
├── .env.example
└── .gitignore
```

## Design Decisions

### Why "Hermes-Inspired" vs. Direct Hermes Integration

Hermes Agent is a standalone CLI application (30k+ stars on GitHub), not a pip-installable library. We adopted its core architectural patterns:

1. **Skills System** — Markdown files with YAML frontmatter, extracted from successful runs
2. **Persistent Memory** — JSON-backed store with keyword search
3. **Closed Learning Loop** — The full cycle: Experience → Skill Extraction → Memory → Trust Updates → Self-Assessment

This approach gives us the benefits of Hermes' architecture while maintaining full control over our domain-specific agent pipeline.

### Kalshi "Pseudo-Traders"

Kalshi does not expose a public trader leaderboard. We model high-volume markets as pseudo-traders, where each market's trading volume serves as a proxy for trader activity. The event ticker prefix (e.g., `KXMLB` → Sports/MLB) enables automatic niche classification.

### Free-Tier LLM Strategy

Uses OpenRouter with three free models in a fallback chain:
1. `mistralai/mistral-7b-instruct:free`
2. `google/gemma-3-4b-it:free`
3. `meta-llama/llama-3.3-70b-instruct:free`

The niche classifier intelligently avoids LLM calls for opaque usernames (like "theo4") that provide no classifiable signal, reserving API calls for descriptive Kalshi market titles.

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_scoring.py -v
```

## License

MIT
