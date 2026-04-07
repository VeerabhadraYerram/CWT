"""CrowdWisdomTrading — Prediction Market AI Agent System.

CLI entry point with Rich-formatted output and interactive chat mode.
"""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agents.orchestrator import Orchestrator
from agents.chat_agent import ChatAgent
from config.settings import settings

console = Console()


def print_banner():
    """Print a startup banner."""
    banner = Text()
    banner.append("🎯 CrowdWisdomTrading", style="bold cyan")
    banner.append(" — Prediction Market AI Agent System\n", style="dim")
    banner.append("   Hermes-inspired multi-agent framework with closed learning loop", style="dim italic")
    console.print(Panel(banner, border_style="cyan"))


def print_traders_table(traders):
    """Display traders in a Rich table."""
    table = Table(
        title="📊 Top Ranked Traders",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan", max_width=35)
    table.add_column("Platform", style="green", width=12)
    table.add_column("Score", style="bold yellow", justify="right", width=7)
    table.add_column("PnL ($)", justify="right", width=14)
    table.add_column("Volume ($)", justify="right", width=14)
    table.add_column("Niche", style="blue", width=16)
    table.add_column("Trust", justify="right", width=6)

    for i, t in enumerate(traders, 1):
        niche = max(t.niches, key=t.niches.get) if t.niches else "GENERAL"
        name = t.display_name or t.wallet_or_username
        if len(name) > 35:
            name = name[:32] + "..."

        pnl_style = "green" if t.total_pnl > 0 else "red"

        table.add_row(
            str(i),
            name,
            t.platform.title(),
            f"{t.composite_score:.1f}",
            f"[{pnl_style}]{t.total_pnl:,.0f}[/{pnl_style}]",
            f"{t.total_volume:,.0f}",
            niche,
            f"{t.trust_score:.0f}",
        )

    console.print(table)


async def run_discovery(limit: int = 10, category: str = "OVERALL"):
    """Run the full discovery pipeline."""
    orchestrator = Orchestrator()
    chat_agent = ChatAgent()

    # Validate API keys
    warnings = settings.validate_keys()
    for w in warnings:
        console.print(f"  {w}", style="yellow")

    console.print()
    console.print("🔍 [bold]Fetching and scoring traders...[/bold]")
    console.print("   Polymarket (real leaderboard) + Kalshi (live markets)", style="dim")
    console.print()

    traders = await orchestrator.discover_traders(category=category, limit=limit)

    if not traders:
        console.print("[bold red]❌ No traders found.[/bold red] APIs may be blocked or rate-limited.")
        await orchestrator.close()
        return None, None

    # Display traders table
    print_traders_table(traders)
    console.print()

    # Generate recommendation
    console.print("🤖 [bold]Generating AI recommendation...[/bold]")
    console.print()

    response = chat_agent.recommend_traders(
        "Which traders should I copy for consistent profits?",
        traders,
    )

    console.print(Panel(
        response,
        title="💡 AI Recommendation",
        border_style="green",
        padding=(1, 2),
    ))

    # Save run log
    try:
        orchestrator.data_store.save_run_log(traders, response)
    except Exception:
        pass

    await orchestrator.close()
    return traders, chat_agent


async def run_chat(traders, chat_agent):
    """Interactive chat loop."""
    console.print()
    console.print(Panel(
        "Ask follow-up questions about traders, markets, or copy-trading strategy.\n"
        "Type [bold]quit[/bold] or [bold]exit[/bold] to stop.",
        title="💬 Interactive Chat",
        border_style="cyan",
    ))

    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]You:[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Chat ended.[/dim]")
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("[dim]Chat ended. Goodbye![/dim]")
            break

        if not user_input.strip():
            continue

        response = chat_agent.chat(user_input, traders)
        console.print()
        console.print(Panel(response, title="🤖 Agent", border_style="green"))


async def main():
    parser = argparse.ArgumentParser(
        description="CrowdWisdomTrading — Prediction Market AI Agent System"
    )
    parser.add_argument("--limit", type=int, default=10, help="Max traders to fetch (default: 10)")
    parser.add_argument("--category", type=str, default="OVERALL", help="Leaderboard category (default: OVERALL)")
    parser.add_argument("--chat", action="store_true", help="Enable interactive chat after discovery")

    args = parser.parse_args()

    print_banner()

    traders, chat_agent = await run_discovery(limit=args.limit, category=args.category)

    if traders and args.chat and chat_agent:
        await run_chat(traders, chat_agent)

    # Print session summary
    console.print()
    console.print("[dim]─── Session Complete ───[/dim]")
    if traders:
        console.print(f"[dim]  Traders analyzed: {len(traders)}[/dim]")
        console.print(f"[dim]  Data persisted to: {settings.DB_PATH}[/dim]")
        console.print(f"[dim]  Skills stored in: {settings.SKILLS_DIR}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())