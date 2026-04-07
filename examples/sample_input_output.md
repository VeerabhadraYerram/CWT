# Sample Input & Output

## Running the Pipeline

### Command
```bash
python main.py --limit 5
```

### Output

```
╭───────────────────────────────────────────────────────────────────╮
│ 🎯 CrowdWisdomTrading — Prediction Market AI Agent System        │
│    Hermes-inspired multi-agent framework with closed learning loop│
╰───────────────────────────────────────────────────────────────────╯

🔍 Fetching and scoring traders...
   Polymarket (real leaderboard) + Kalshi (live markets)

[info] pipeline_start         category=OVERALL pipeline=discover_traders
[info] traders_fetched        agent=polymarket_agent count=5
[info] kalshi_traders_created agent=kalshi_agent count=5
[info] step_done              count=10 step=niche_mapping
[info] apify_search           query='📈 Elon Mars Mkt prediction market analysis'
[info] apify_search_done      results=3
[info] pipeline_done          kalshi_count=5 polymarket_count=5 top_score=89.48

                 📊 Top Ranked Traders & Markets
┏━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━┓
┃ #  ┃ Trader / Market   ┃ Platform   ┃ Score ┃       PnL ($) ┃   Volume ($)  ┃ Niche         ┃ Trust┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━┩
│ 1  │ kch123            │ Polymarket │  89.5 │    11,456,526 │  276,451,914  │ GENERAL       │   50 │
│ 2  │ Theo4             │ Polymarket │  88.6 │    22,053,934 │   43,013,259  │ GENERAL       │   50 │
│ 3  │ Fredi9999         │ Polymarket │  88.4 │    16,619,507 │   76,611,317  │ GENERAL       │   50 │
│ 4  │ swisstony         │ Polymarket │  87.4 │     5,730,170 │  631,274,627  │ GENERAL       │   50 │
│ 5  │ RN1               │ Polymarket │  87.2 │     6,973,362 │  373,554,064  │ GENERAL       │   50 │
│ 6  │ 📈 Elon Mars Mkt  │ Kalshi     │  32.1 │         3,498 │       69,965  │ SCIENCE/TECH  │   50 │
│ 7  │ 📈 Next Pope Mkt  │ Kalshi     │  28.5 │           646 │       12,926  │ GENERAL       │   50 │
│ 8  │ 📈 Btc Price Mkt  │ Kalshi     │  26.8 │           582 │       11,635  │ CRYPTO        │   50 │
│ 9  │ 📈 Nfl Mkt        │ Kalshi     │  24.3 │           446 │        8,923  │ SPORTS        │   50 │
│ 10 │ 📈 Weather Mkt    │ Kalshi     │  22.1 │         1,299 │       25,988  │ WEATHER       │   50 │
└────┴───────────────────┴────────────┴───────┴───────────────┴───────────────┴───────────────┴──────┘
```

### AI Recommendation

```
╭────────────────────── 💡 AI Recommendation ──────────────────────╮
│                                                                   │
│  🏆 **kch123** is the top-ranked trader to copy.                  │
│                                                                   │
│  📊 Score: 89.48/100                                              │
│  💰 PnL: $11,456,526.22                                           │
│  📈 Volume: $276,451,914.46                                       │
│  🏷️ Platform: Polymarket                                          │
│                                                                   │
│  They stand out due to strong profitability and high trading      │
│  activity compared to 10 other traders analyzed.                  │
│                                                                   │
╰───────────────────────────────────────────────────────────────────╯
```

---

## Interactive Chat Mode

### Command
```bash
python main.py --chat --limit 5
```

### Chat Session Examples

The chat system uses LLM when available, with intelligent data-driven fallbacks when rate-limited:

```
╭───────────────── 💬 Interactive Chat ─────────────────╮
│ Ask follow-up questions about traders, markets, or    │
│ copy-trading strategy.                                │
│ Type quit or exit to stop.                            │
╰───────────────────────────────────────────────────────╯

You: What is the best trading strategy?
╭────────────── 🤖 Agent ──────────────╮
│ 📊 **Trading Strategy Analysis**:    │
│                                      │
│ Based on the top traders analyzed:   │
│   • Copy top-scorers: kch123 leads   │
│     with 89.5/100                    │
│   • Diversify platforms: Mix         │
│     Polymarket + Kalshi              │
│   • Track volume: Higher volume =    │
│     more liquid, safer to follow     │
│   • Watch win rate: Target >50%      │
│   • Size positions: Start small      │
│                                      │
│ 🏆 Top trader: kch123               │
│    ($11,456,526 PnL, Polymarket)     │
╰──────────────────────────────────────╯

You: Which trader has the best risk/reward ratio?
╭────────────── 🤖 Agent ──────────────╮
│ 📊 **Risk/Reward Analysis**:         │
│                                      │
│   1. Theo4 — ratio: 51.27%,         │
│      PnL: $22,053,934                │
│   2. Fredi9999 — ratio: 21.69%,     │
│      PnL: $16,619,507                │
│   3. kch123 — ratio: 4.14%,         │
│      PnL: $11,456,526                │
│                                      │
│ 💡 Higher PnL/Volume ratio =         │
│    better capital efficiency.         │
╰──────────────────────────────────────╯

You: Compare the top two traders
╭────────────── 🤖 Agent ──────────────╮
│ 📊 **Head-to-Head Comparison**:      │
│                                      │
│ | Metric   | kch123      | Theo4    |│
│ |----------|-------------|----------|│
│ | Score    | 89.5        | 88.6     |│
│ | PnL      | $11,456,526 | $22M    |│
│ | Volume   | $276M       | $43M    |│
│ | Platform | Polymarket  | Polym.  |│
│ | Trades   | 500         | 350     |│
╰──────────────────────────────────────╯

You: Tell me about Kalshi markets
╭────────────── 🤖 Agent ──────────────╮
│ 📊 **Platform Breakdown**:           │
│                                      │
│ Polymarket — 5 traders, avg: 86.2    │
│   Top: kch123 ($11,456,526 PnL)     │
│                                      │
│ Kalshi — 5 markets, avg: 26.8        │
│   Top: 📈 Elon Mars Mkt ($3,498)    │
╰──────────────────────────────────────╯

You: quit
Chat ended. Goodbye!
```

---

## Notes

- **Kalshi entries** are labeled with 📈 and display as market names (e.g., "📈 Elon Mars Mkt") because Kalshi doesn't expose individual trader data — each entry represents collective market activity.
- **Polymarket entries** are real trader usernames from the public leaderboard.
- The chat fallback system handles **10+ types of questions** without LLM: strategy, risk/reward, comparisons, platforms, niches, volume, PnL, rankings, and general summaries.
- When LLM models are available, responses are richer and more conversational.
- **VPN**: Kalshi API may require a US-based VPN (Cloudflare WARP works). Polymarket, OpenRouter, and Apify work globally.
