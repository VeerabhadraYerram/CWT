# Sample Input / Output

Real output from a production run of the CrowdWisdomTrading agent system.

---

## Run: Default Discovery (`python main.py --limit 8`)

### Command

```bash
python main.py --limit 8
```

### Pipeline Execution Log

```
╭──────────────────────────╮
│ 🎯 CrowdWisdomTrading —  │
│ Prediction Market AI     │
│ Agent System             │
│    Hermes-inspired       │
│ multi-agent framework    │
│ with closed learning     │
│ loop                     │
╰──────────────────────────╯

🔍 Fetching and scoring traders...
   Polymarket (real leaderboard) + Kalshi (live markets)

[info] pipeline_start          category=OVERALL
[info] fetch_traders           agent=polymarket_agent limit=8
[info] polymarket_leaderboard  category=OVERALL limit=8
[info] traders_fetched         agent=polymarket_agent count=8
[info] step_done               step=polymarket_fetch count=8

[info] kalshi_fetch_traders    agent=kalshi_agent limit=8
[info] kalshi_get_markets      limit=8 status=open
[info] kalshi_markets_fetched  count=8
[info] step_done               step=kalshi_fetch count=8

[info] step_done               step=niche_mapping count=16
[info] step_done               step=rag_enrichment events=3
[info] step_done               step=scoring total=16

[info] traders_saved           count=16
[info] step_done               step=persistence

[info] learning_loop_start     trader_count=16
[info] memory_saved            category=run_outcome id=mem_0004
[info] skill_saved             name=insight_20260407_1448
[info] memory_saved            category=self_assessment id=mem_0005
[info] learning_loop_done      memories=2 skills=1
[info] step_done               step=learning_loop

[info] pipeline_done           total=16 top_score=89.48
```

### Trader Rankings Table

```
     📊 Top Ranked Traders
┏━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━┓
┃# ┃ Name          ┃ Platform  ┃ Score ┃      PnL ($) ┃  Volume ($)  ┃ Niche      ┃Trust ┃
┡━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━┩
│1 │ kch123        │ Polymarket│  89.5 │  11,456,526  │ 276,451,914  │ GENERAL    │  50  │
│2 │ theo4         │ Polymarket│  84.2 │  22,841,128  │ 437,982,665  │ GENERAL    │  50  │
│3 │ fredi9999     │ Polymarket│  78.9 │  16,332,941  │ 763,234,812  │ GENERAL    │  50  │
│4 │ zxgngl        │ Polymarket│  72.1 │   6,128,556  │ 374,821,944  │ GENERAL    │  50  │
│5 │ princesscaro  │ Polymarket│  68.8 │   7,229,114  │ 403,612,221  │ GENERAL    │  50  │
│6 │ len9311238    │ Polymarket│  65.2 │   8,445,773  │ 162,554,382  │ GENERAL    │  50  │
│7 │ rn1           │ Polymarket│  61.0 │   6,118,224  │ 233,441,891  │ GENERAL    │  50  │
│8 │ Michiel99     │ Polymarket│  58.4 │   7,882,312  │ 138,228,447  │ POLITICS   │  50  │
└──┴───────────────┴───────────┴───────┴──────────────┴──────────────┴────────────┴──────┘
```

### AI Recommendation

```
╭── 💡 AI Recommendation ──╮
│                           │
│  🏆 **kch123** is the     │
│  top-ranked trader to     │
│  copy.                    │
│                           │
│  📊 Score: 89.48/100      │
│  💰 PnL: $11,456,526.22   │
│  📈 Volume:               │
│  $276,451,914.46          │
│  🏷️ Platform: Polymarket  │
│                           │
│  They stand out due to    │
│  strong profitability     │
│  and high trading         │
│  activity compared to 8   │
│  other traders analyzed.  │
│                           │
╰───────────────────────────╯
```

### Session Summary

```
─── Session Complete ───
  Traders analyzed: 8
  Data persisted to: data/predictions.db
  Skills stored in: memory/store/skills
```

---

## Run: Interactive Chat (`python main.py --chat`)

```bash
python main.py --limit 5 --chat
```

After the discovery pipeline runs, the interactive chat mode begins:

```
╭── 💬 Interactive Chat ──╮
│ Ask follow-up questions  │
│ about traders, markets,  │
│ or copy-trading strategy │
│ Type quit or exit to     │
│ stop.                    │
╰──────────────────────────╯

You: Which trader has the best risk/reward ratio?

╭── 🤖 Agent ──────────────╮
│ Based on the data,        │
│ kch123 offers the best    │
│ risk/reward ratio with    │
│ PnL of $11.5M on $276M   │
│ volume (4.1% return).     │
╰───────────────────────────╯

You: quit
Chat ended. Goodbye!
```

---

## Generated Artifacts

After a run, the following files are created in `data/` and `memory/store/`:

### Skill File: `memory/store/skills/insight_20260407_1448.md`

```markdown
---
name: insight_20260407_1448
description: Auto-extracted from pipeline run analyzing 16 traders
tags: [auto-extracted, polymarket, general]
created: 2026-04-07T14:48:58.000000+00:00
---

When analyzing polymarket traders, prioritize those with
PnL > $11,456,526 and volume > $276,451,914.
These high-value traders tend to score well (score: 89.48/100).
```

### Memory: `memory/store/memory.json` (excerpt)

```json
[
  {
    "id": "mem_0004",
    "content": "Pipeline run at 2026-04-07T14:48:58...\nTotal traders analyzed: 16\nTop 5 traders:\n  - kch123 (polymarket) | Score: 89.48 | PnL: $11,456,526",
    "category": "run_outcome",
    "tags": ["pipeline", "traders", "recommendation"]
  }
]
```

---

## Test Results

```bash
$ python -m pytest tests/ -v

tests/test_scoring.py::TestTraderScorer::test_score_with_trade_data PASSED
tests/test_scoring.py::TestTraderScorer::test_score_without_trade_data PASSED
tests/test_scoring.py::TestTraderScorer::test_score_clamping PASSED
tests/test_scoring.py::TestTraderScorer::test_score_zero_everything PASSED
tests/test_scoring.py::TestTraderScorer::test_rank_ordering PASSED
tests/test_scoring.py::TestTraderScorer::test_rank_scores_set PASSED
tests/test_scoring.py::TestTraderScorer::test_breakdown_with_trades PASSED
tests/test_scoring.py::TestTraderScorer::test_breakdown_without_trades PASSED
tests/test_scoring.py::TestTraderScorer::test_recency_decay PASSED
tests/test_scoring.py::TestTraderScorer::test_higher_winrate_scores_better PASSED
tests/test_agents.py::TestTraderProfile::test_create_minimal PASSED
tests/test_agents.py::TestTraderProfile::test_score_clamping PASSED
tests/test_agents.py::TestTraderProfile::test_computed_win_rate PASSED
tests/test_agents.py::TestTraderProfile::test_computed_win_rate_zero_trades PASSED
tests/test_agents.py::TestTraderProfile::test_to_summary_dict PASSED
tests/test_agents.py::TestNicheAgent::test_politics_keyword PASSED
tests/test_agents.py::TestNicheAgent::test_sports_keyword PASSED
tests/test_agents.py::TestNicheAgent::test_weather_keyword PASSED
tests/test_agents.py::TestNicheAgent::test_general_fallback PASSED
tests/test_agents.py::TestNicheAgent::test_preserves_existing_niches PASSED
tests/test_agents.py::TestMemoryManager::test_save_and_search PASSED
tests/test_agents.py::TestMemoryManager::test_get_recent PASSED
tests/test_agents.py::TestMemoryManager::test_count PASSED
tests/test_agents.py::TestMemoryManager::test_clear PASSED
tests/test_agents.py::TestSkillsManager::test_save_and_load PASSED
tests/test_agents.py::TestSkillsManager::test_list_skills PASSED
tests/test_agents.py::TestSkillsManager::test_find_relevant PASSED
tests/test_agents.py::TestSkillsManager::test_delete_skill PASSED

======================== 28 passed in 0.37s =========================
```
