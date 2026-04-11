#!/usr/bin/env python3
"""
Automation Hub — CLI Entry Point

Usage:
  python run.py --status      # System status dashboard
  python run.py --briefing    # Generate morning briefing
  python run.py --jobs        # Run job discovery + tailoring pipeline
  python run.py --linkedin    # Generate + interactively review LinkedIn post
  python run.py --gmail       # Run Gmail triage
  python run.py --telegram    # Start Telegram bot (blocking)
  python run.py --schedule    # Start full APScheduler daemon (blocking)
  python run.py --setup       # First-time setup wizard — writes .env
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv()

console = Console()

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ── logging ───────────────────────────────────────────────

def _setup_logging() -> None:
    from logging.handlers import RotatingFileHandler

    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            LOG_DIR / f"{date.today().isoformat()}.log",
            maxBytes=5_242_880,
            backupCount=7,
        ),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


# ── environment validation ────────────────────────────────

REQUIRED_VARS: dict[str, str] = {
    "ANTHROPIC_API_KEY": "Required for Claude AI — console.anthropic.com",
}
OPTIONAL_VARS: dict[str, str] = {
    "LINKEDIN_ACCESS_TOKEN": "LinkedIn API token — developers.linkedin.com",
    "LINKEDIN_PERSON_URN":   "Your LinkedIn URN (urn:li:person:XXXXX)",
    "TELEGRAM_BOT_TOKEN":    "Telegram bot token — create via @BotFather",
    "TELEGRAM_CHAT_ID":      "Your Telegram chat ID — get via @userinfobot",
    "GMAIL_CREDENTIALS_PATH":"Path to Gmail OAuth credentials.json",
}


def _validate_env() -> bool:
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        console.print("\n[bold red]Missing required environment variables:[/bold red]")
        for v in missing:
            console.print(f"  • {v}: {REQUIRED_VARS[v]}")
        console.print("\nRun [bold]python run.py --setup[/bold] for guided setup.\n")
        return False
    return True


# ── --status ──────────────────────────────────────────────

def cmd_status() -> None:
    """Print system status dashboard: env vars, job DB counts, LinkedIn token age."""
    from src.services.automation import get_environment_status, get_linkedin_status

    console.print()
    console.print(Panel(
        f"[bold]Automation Hub[/bold] — {date.today().isoformat()}",
        border_style="cyan",
    ))

    # Environment table
    env = get_environment_status()
    env_table = Table(title="Environment", show_lines=False)
    env_table.add_column("Variable", style="bold", no_wrap=True)
    env_table.add_column("Status", min_width=22)
    env_table.add_column("Description", style="dim")
    for var, info in env.items():
        if info["set"]:
            status_cell = "[green]✓ set[/green]"
        elif info["required"]:
            status_cell = "[red]✗ missing (required)[/red]"
        else:
            status_cell = "[yellow]○ not set[/yellow]"
        env_table.add_row(var, status_cell, info["description"][:55])
    console.print(env_table)

    # Job counts direct from DB
    console.print("\n[bold]📋 Job Pipeline[/bold]")
    db_path = REPO_ROOT / "data" / "jobs.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        try:
            total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
            today_str = date.today().isoformat()
            today_count = conn.execute(
                "SELECT COUNT(*) FROM seen_jobs WHERE date_seen = ?", (today_str,)
            ).fetchone()[0]
            by_status = dict(
                conn.execute(
                    "SELECT status, COUNT(*) FROM seen_jobs GROUP BY status"
                ).fetchall()
            )
        finally:
            conn.close()
        console.print(f"  Total tracked : {total}")
        console.print(f"  Today's queue : {today_count}")
        for s, c in by_status.items():
            console.print(f"    {s}: {c}")
    else:
        console.print("  [dim]No database found — run [bold]--jobs[/bold] first.[/dim]")

    # LinkedIn token age
    li = get_linkedin_status()
    console.print(f"\n[bold]💼 LinkedIn[/bold]: {li['status']}")
    if li.get("token_warning"):
        console.print(f"  [red]⚠  {li['token_warning']}[/red]")
    elif li.get("token_age_days") is not None:
        console.print(f"  Token age: {li['token_age_days']} days")

    console.print()


# ── --briefing ────────────────────────────────────────────

def cmd_briefing() -> None:
    """Generate and display morning briefing via generate_briefing()."""
    from src.briefing.morning_briefing import generate_briefing

    console.print("\n[bold]☀️  Generating morning briefing...[/bold]\n")
    briefing = generate_briefing()
    console.print(Panel(briefing, title="Morning Briefing", border_style="cyan"))

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat  = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            from src.messaging.telegram_bot import send_message_sync
            send_message_sync(briefing)
            console.print("[green]Sent to Telegram.[/green]")
        except Exception as exc:
            console.print(f"[yellow]Telegram send failed: {exc}[/yellow]")
    console.print()


# ── --jobs ────────────────────────────────────────────────

def cmd_jobs() -> None:
    """Run job discovery + resume tailoring pipeline."""
    from src.services.automation import run_jobs_pipeline

    console.print("\n[bold]🔍 Running job pipeline...[/bold]\n")
    result = run_jobs_pipeline()

    discovered  = result.get("scraped_new_jobs", 0)
    tailored    = result.get("tailored_jobs", 0)
    queue_today = result.get("queue_size_today", 0)

    console.print(f"  Discovered  : [green]{discovered}[/green] new jobs")
    console.print(f"  Tailored    : [green]{tailored}[/green] resumes")
    console.print(f"  Queue today : {queue_today} jobs")

    stats = result.get("stats", {})
    if stats.get("by_status"):
        console.print("\n[bold]Status breakdown:[/bold]")
        for s, c in stats["by_status"].items():
            console.print(f"  {s}: {c}")

    console.print()


# ── --linkedin ────────────────────────────────────────────

def cmd_linkedin() -> None:
    """Generate post for today's pillar then open interactive review gate."""
    from src.linkedin.reviewer import review_post

    console.print("\n[bold]💼 LinkedIn Post Workflow[/bold]\n")
    review_post()  # generates if not in queue, then prompts P/E/R/S


# ── --gmail ───────────────────────────────────────────────

def cmd_gmail() -> None:
    """Run Gmail triage and print structured summary."""
    from src.services.automation import run_gmail_triage_now

    console.print("\n[bold]📧 Running Gmail triage...[/bold]\n")
    result = run_gmail_triage_now(send_to_telegram=False)

    console.print(Panel(result["summary"], title="Gmail Triage", border_style="blue"))

    urgent = result.get("urgent_count", 0)
    normal = result.get("normal_count", 0)
    console.print(f"\n  Urgent: [red]{urgent}[/red]   Normal: {normal}")

    if result.get("decision_needed"):
        console.print("\n[bold red]⚠  Urgent emails require your attention.[/bold red]")

    console.print()


# ── --telegram ────────────────────────────────────────────

def cmd_telegram() -> None:
    """Start the Telegram bot (blocking until Ctrl+C)."""
    from src.messaging.telegram_bot import start_bot

    console.print("\n[bold]🤖 Starting Telegram bot...[/bold]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")
    start_bot()


# ── --schedule ────────────────────────────────────────────

def cmd_schedule() -> None:
    """Start the full APScheduler daemon (blocking until Ctrl+C)."""
    from src.scheduler.cron import start_scheduler

    console.print("\n[bold]📅 Starting scheduler...[/bold]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")
    start_scheduler()


# ── --setup ───────────────────────────────────────────────

def cmd_setup() -> None:
    """Interactive first-time setup wizard — reads / writes .env."""
    console.print(Panel(
        "[bold]Automation Hub — Setup Wizard[/bold]\n\n"
        "Configure each service. Leave any prompt blank to keep the current value.",
        border_style="cyan",
    ))

    env_path = REPO_ROOT / ".env"

    # Load existing .env values
    existing: dict[str, str] = {}
    if env_path.exists():
        console.print("[yellow]Existing .env found — values will be updated.[/yellow]\n")
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw and not raw.startswith("#") and "=" in raw:
                k, _, v = raw.partition("=")
                existing[k.strip()] = v.strip()

    def ask(name: str, label: str, default: str = "") -> str:
        current = os.getenv(name) or existing.get(name, default)
        hint = f" [dim](current: {current[:28]}…)[/dim]" if current else ""
        entered = console.input(f"  {label}{hint}: ").strip()
        return entered or current

    updates: dict[str, str] = {}

    # 1 / 4  Anthropic
    console.print("\n[bold]1 / 4 — Anthropic (Claude AI)[/bold]")
    console.print("  Get your key at https://console.anthropic.com/")
    if v := ask("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"):
        updates["ANTHROPIC_API_KEY"] = v

    # 2 / 4  LinkedIn
    console.print("\n[bold]2 / 4 — LinkedIn[/bold]")
    if console.input("  Open LinkedIn token generator in browser? [y/N]: ").strip().lower() == "y":
        webbrowser.open("https://www.linkedin.com/developers/tools/oauth/token-generator")
    if v := ask("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ACCESS_TOKEN"):
        updates["LINKEDIN_ACCESS_TOKEN"] = v
        updates["LINKEDIN_PERSON_URN"] = ask(
            "LINKEDIN_PERSON_URN", "LINKEDIN_PERSON_URN", "urn:li:person:XXXXXXX"
        )
        updates["LINKEDIN_TOKEN_SET_DATE"] = date.today().isoformat()

    # 3 / 4  Telegram
    console.print("\n[bold]3 / 4 — Telegram[/bold]")
    console.print("  Message @BotFather to create a bot, @userinfobot for your chat ID.")
    if v := ask("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"):
        updates["TELEGRAM_BOT_TOKEN"] = v
    if v := ask("TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"):
        updates["TELEGRAM_CHAT_ID"] = v

    # 4 / 4  Gmail
    console.print("\n[bold]4 / 4 — Gmail (optional)[/bold]")
    console.print("  Download credentials.json from Google Cloud Console → APIs & Services.")
    creds = ask("GMAIL_CREDENTIALS_PATH", "Path to credentials.json", "credentials.json")
    updates["GMAIL_CREDENTIALS_PATH"] = creds
    updates["GMAIL_TOKEN_PATH"] = existing.get("GMAIL_TOKEN_PATH", "token.json")

    # Preserve / set defaults
    for key, default in {
        "TIMEZONE":              "America/New_York",
        "DAILY_JOB_LIMIT":      "10",
        "POST_TIME_WINDOW_START":"8",
        "POST_TIME_WINDOW_END":  "11",
    }.items():
        updates.setdefault(key, existing.get(key, default))

    # Write merged .env (existing keys not touched by wizard are preserved)
    merged = {**existing, **updates}
    lines = [f"# Automation Hub — generated {datetime.now().isoformat()}", ""]
    lines += [f"{k}={v}" for k, v in merged.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"\n[green]✅ .env written → {env_path}[/green]")

    # Create output tree
    for rel in [
        "output/linkedin/queue",
        "output/linkedin/posted",
        "output/jobs",
        "output/briefings",
        "output/tailored_resumes",
        "output/token_logs",
        "data",
        "logs",
    ]:
        (REPO_ROOT / rel).mkdir(parents=True, exist_ok=True)
    console.print("[green]✅ Output directories created.[/green]")

    # Init DB
    from src.jobs.deduplicator import init_db
    init_db()
    console.print("[green]✅ SQLite database initialised.[/green]")

    # Smoke-test Claude API
    api_key = updates.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        console.print("\n[bold]Testing Claude API connection...[/bold]")
        try:
            from src.agent.claude_client import ClaudeClient
            ClaudeClient().complete("Reply with the single word OK.")
            console.print("  [green]✓ Claude API connected.[/green]")
        except Exception as exc:
            console.print(f"  [red]✗ Claude API error: {exc}[/red]")

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("  python run.py --status    → verify everything")
    console.print("  python run.py --jobs      → first job search")
    console.print("  python run.py --linkedin  → generate first post")
    console.print("  python run.py --schedule  → start the scheduler\n")


# ── main ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automation Hub — personal AI automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  --setup       First-time setup wizard (writes .env)
  --status      System status dashboard
  --briefing    Generate morning briefing
  --jobs        Job discovery + resume tailoring
  --linkedin    Generate + review LinkedIn post
  --gmail       Gmail triage
  --telegram    Start Telegram bot
  --schedule    Start full scheduler
        """,
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--setup",    action="store_true", help="First-time setup wizard")
    g.add_argument("--status",   action="store_true", help="System status dashboard")
    g.add_argument("--briefing", action="store_true", help="Generate morning briefing")
    g.add_argument("--jobs",     action="store_true", help="Job discovery + tailoring")
    g.add_argument("--linkedin", action="store_true", help="Generate + review LinkedIn post")
    g.add_argument("--gmail",    action="store_true", help="Run Gmail triage")
    g.add_argument("--telegram", action="store_true", help="Start Telegram bot")
    g.add_argument("--schedule", action="store_true", help="Start full scheduler")

    args = parser.parse_args()
    _setup_logging()

    # --setup and --status don't need ANTHROPIC_API_KEY
    if args.setup:
        cmd_setup()
        return
    if args.status:
        cmd_status()
        return

    if not _validate_env():
        sys.exit(1)

    if args.briefing:
        cmd_briefing()
    elif args.jobs:
        cmd_jobs()
    elif args.linkedin:
        cmd_linkedin()
    elif args.gmail:
        cmd_gmail()
    elif args.telegram:
        cmd_telegram()
    elif args.schedule:
        cmd_schedule()


if __name__ == "__main__":
    main()
