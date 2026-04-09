#!/usr/bin/env python3
"""
Automation Hub CLI — Master Command Interface

Extends run.py with profile management, token tracking, and decision-support.

Usage:
  # Profile management
  python cli.py profile set soumyabrata     # Switch profile
  python cli.py profile show                # Show current profile
  python cli.py profile list                # List all profiles

  # Job search
  python cli.py jobs --dry-run              # Simulate (no API calls)
  python cli.py jobs                        # Full pipeline
  python cli.py jobs review                 # Review discovered jobs queue

  # Automation
  python cli.py gmail                       # Triage emails
  python cli.py linkedin draft              # Draft next post
  python cli.py briefing                    # Generate morning briefing

  # System
  python cli.py status                      # System status dashboard
  python cli.py tokens report               # Token usage report
  python cli.py config validate             # Validate configuration
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv()
console = Console()

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging."""
    from logging.handlers import RotatingFileHandler

    log_dir = REPO_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    handlers = [
        RotatingFileHandler(log_dir / f"{date.today().isoformat()}.log", maxBytes=5_242_880, backupCount=7),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


# ── Profile Commands ──────────────────────────────────────────

def cmd_profile_set(profile_name: str):
    """Set active profile."""
    from src.config.profile_manager import set_active_profile

    if set_active_profile(profile_name):
        console.print(f"[green]✅ Profile set to: {profile_name}[/green]")
    else:
        console.print(f"[red]❌ Failed to set profile: {profile_name}[/red]")
        sys.exit(1)


def cmd_profile_show():
    """Show current profile."""
    from src.config.profile_manager import get_active_profile_name, load_profile, validate_profile

    profile_name = get_active_profile_name()
    profile = load_profile(profile_name)
    valid, errors = validate_profile(profile)

    console.print(f"\n[bold]📋 Active Profile: {profile_name}[/bold]\n")

    if not valid:
        console.print("[red]⚠ Profile has validation errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        return

    # Show profile table
    table = Table(title="Profile Information", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Name", profile.get("name", "?"))
    table.add_row("Email", profile.get("email", "?"))
    table.add_row("Phone", profile.get("phone", "?"))
    table.add_row("Location", profile.get("location", "?"))

    job_prefs = profile.get("job_preferences", {})
    roles = job_prefs.get("target_roles", [])
    table.add_row("Target Roles", f"{len(roles)} roles configured")

    keywords = job_prefs.get("target_keywords", [])
    table.add_row("Target Keywords", f"{len(keywords)} keywords")

    locations = job_prefs.get("locations", [])
    table.add_row("Locations", ", ".join(locations[:3]))

    console.print(table)
    console.print()


def cmd_profile_list():
    """List available profiles."""
    from src.config.profile_manager import get_profiles_dir, get_active_profile_name

    profiles_dir = get_profiles_dir()
    profiles = sorted(profiles_dir.glob("*.yaml"))
    active = get_active_profile_name()

    console.print(f"\n[bold]📂 Available Profiles ({len(profiles)})[/bold]\n")

    for profile_path in profiles:
        name = profile_path.stem
        marker = "✅" if name == active else "  "
        console.print(f"  {marker} {name}")

    console.print()


# ── Job Commands ──────────────────────────────────────────────

def cmd_jobs(dry_run: bool = False, action: str = "run"):
    """Run job discovery pipeline."""
    from src.services.automation import run_jobs_pipeline

    if action == "review":
        # Show job queue for review
        from src.jobs.deduplicator import get_todays_queue

        queue = get_todays_queue()
        console.print(f"\n[bold]📋 Today's Job Queue ({len(queue)} jobs)[/bold]\n")

        if not queue:
            console.print("  (no jobs discovered yet)")
            return

        table = Table(show_lines=False)
        table.add_column("Company", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Status")

        for job in queue[:10]:
            table.add_row(
                job.get("company", "?"),
                job.get("title", "?"),
                job.get("status", "pending"),
            )

        console.print(table)
        console.print()
        return

    if dry_run:
        console.print("[yellow]⚠ DRY RUN (no API calls, using demo data)[/yellow]\n")
        from dry_run_phase1 import demo_job_discovery

        jobs = demo_job_discovery()
        return

    console.print("[bold]🔍 Running job discovery pipeline...[/bold]\n")
    result = run_jobs_pipeline()

    console.print(f"[green]✅ Pipeline complete[/green]\n")
    console.print(f"  Discovered: {result.get('discovered_jobs', 0)} jobs")
    console.print(f"  Queued: {result.get('queued_jobs', 0)} jobs")
    console.print(f"  Tailored: {result.get('tailored_jobs', 0)} resumes")

    if result.get("errors"):
        console.print(f"\n[yellow]⚠ Errors:[/yellow]")
        for error in result["errors"]:
            console.print(f"  • {error}")

    console.print()


# ── Gmail Commands ─────────────────────────────────────────────

def cmd_gmail():
    """Run Gmail triage."""
    from src.services.automation import run_gmail_triage_now

    console.print("[bold]📧 Running Gmail triage...[/bold]\n")

    try:
        result = run_gmail_triage_now(send_to_telegram=False)
        console.print(Panel(result["summary"], title="Gmail Triage", border_style="cyan"))

        if result.get("decision_needed"):
            console.print("\n[red]⚠ URGENT EMAILS DETECTED[/red] — Review and act immediately!")

    except Exception as exc:
        console.print(f"[red]❌ Gmail triage error: {exc}[/red]")
        logger.error(f"Gmail triage error: {exc}", exc_info=True)


# ── LinkedIn Commands ──────────────────────────────────────────

def cmd_linkedin(action: str = "draft"):
    """LinkedIn workflow."""
    if action == "draft":
        console.print("[bold]💼 LinkedIn Draft Mode[/bold]\n")
        console.print("  [yellow]Feature coming in Phase 2[/yellow]\n")
    elif action == "review":
        console.print("[bold]💼 LinkedIn Review Queue[/bold]\n")
        queue_dir = REPO_ROOT / "output" / "linkedin" / "queue"
        if queue_dir.exists():
            drafts = list(queue_dir.glob("*.md"))
            console.print(f"  {len(drafts)} drafts awaiting review\n")
        else:
            console.print("  (no drafts)\n")


# ── System Commands ───────────────────────────────────────────

def cmd_status():
    """System status dashboard."""
    from src.services.automation import get_system_status, get_environment_status

    snapshot = get_system_status()
    env = snapshot["environment"]

    console.print()
    console.print(Panel(
        f"[bold]Automation Hub Status[/bold] — {snapshot['date']}",
        border_style="cyan",
    ))

    # Environment
    env_table = Table(title="Environment", show_lines=False)
    env_table.add_column("Variable", style="bold")
    env_table.add_column("Status")

    for var, info in env.items():
        status = "[green]✓[/green]" if info["set"] else (
            "[red]✗ Required[/red]" if info["required"] else "[yellow]○ Optional[/yellow]"
        )
        env_table.add_row(var, status)

    console.print(env_table)

    # Jobs
    jobs = snapshot["jobs"]
    console.print(f"\n[bold]📋 Job Pipeline[/bold]")
    console.print(f"  Total tracked: {jobs.get('total_jobs', 0)}")
    console.print(f"  Today's queue: {jobs.get('today_queued', 0)}")

    # LinkedIn
    linkedin = snapshot["linkedin"]
    console.print(f"\n[bold]💼 LinkedIn[/bold]")
    console.print(f"  Status: {linkedin['status']}")

    console.print()


def cmd_tokens_report():
    """Show token usage report."""
    log_dir = REPO_ROOT / "output" / "token_logs"

    if not log_dir.exists() or not list(log_dir.glob("*.json")):
        console.print("\n[yellow]ℹ No token logs found yet[/yellow]\n")
        return

    console.print("\n[bold]📊 Token Usage Report[/bold]\n")

    # Load latest summary
    latest = sorted(log_dir.glob("*_summary.json"))[-1]

    with open(latest, "r", encoding="utf-8") as f:
        summary = json.load(f)

    table = Table(title="Token Usage by Skill", show_lines=False)
    table.add_column("Skill", style="bold")
    table.add_column("Calls", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right")

    total_tokens = 0
    total_cost = 0.0

    for skill, data in summary.get("by_skill", {}).items():
        tokens = data.get("total_tokens", 0)
        cost = data.get("estimated_cost_usd", 0.0)
        calls = data.get("count", 0)

        table.add_row(
            skill,
            str(calls),
            f"{tokens:,}",
            f"${cost:.4f}",
        )

        total_tokens += tokens
        total_cost += cost

    console.print(table)

    console.print(f"\n  [bold]Total:[/bold] {total_tokens:,} tokens (${total_cost:.6f})")
    console.print(f"  [dim]From: {summary['start_time']}[/dim]\n")


def cmd_config_validate():
    """Validate configuration."""
    from src.config.profile_manager import load_profile, validate_profile

    profile = load_profile()
    valid, errors = validate_profile(profile)

    console.print("\n[bold]🔍 Configuration Validation[/bold]\n")

    if valid:
        console.print("[green]✅ All systems configured correctly[/green]\n")
    else:
        console.print("[red]❌ Configuration errors found:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print()


# ── Main ──────────────────────────────────────────────────────

def main():
    """Main CLI entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Automation Hub CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Profile management
  python cli.py profile set soumyabrata
  python cli.py profile show

  # Job search
  python cli.py jobs --dry-run
  python cli.py jobs

  # System
  python cli.py status
  python cli.py tokens report
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Profile subcommand
    profile_parser = subparsers.add_parser("profile", help="Profile management")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_action")
    profile_subparsers.add_parser("set", help="Set active profile").add_argument("name")
    profile_subparsers.add_parser("show", help="Show current profile")
    profile_subparsers.add_parser("list", help="List all profiles")

    # Jobs subcommand
    jobs_parser = subparsers.add_parser("jobs", help="Job search pipeline")
    jobs_parser.add_argument("--dry-run", action="store_true", help="Dry run (demo data)")
    jobs_parser.add_argument("action", nargs="?", default="run", choices=["run", "review"])

    # Gmail subcommand
    subparsers.add_parser("gmail", help="Gmail triage")

    # LinkedIn subcommand
    linkedin_parser = subparsers.add_parser("linkedin", help="LinkedIn workflow")
    linkedin_parser.add_argument("action", nargs="?", default="draft", choices=["draft", "review"])

    # System subcommand
    system_parser = subparsers.add_parser("system", help="System management")
    system_subparsers = system_parser.add_subparsers(dest="system_action")
    system_subparsers.add_parser("status", help="Status dashboard")

    # Tokens subcommand
    tokens_parser = subparsers.add_parser("tokens", help="Token tracking")
    tokens_subparsers = tokens_parser.add_subparsers(dest="tokens_action")
    tokens_subparsers.add_parser("report", help="Usage report")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    config_subparsers.add_parser("validate", help="Validate configuration")

    # Status shortcut
    subparsers.add_parser("status", help="System status (shortcut)")

    args = parser.parse_args()

    # Route commands
    if args.command == "profile":
        if args.profile_action == "set":
            cmd_profile_set(args.name)
        elif args.profile_action == "show":
            cmd_profile_show()
        elif args.profile_action == "list":
            cmd_profile_list()
    elif args.command == "jobs":
        cmd_jobs(dry_run=args.dry_run, action=args.action)
    elif args.command == "gmail":
        cmd_gmail()
    elif args.command == "linkedin":
        cmd_linkedin(args.action)
    elif args.command in ("system", "status"):
        if args.command == "system":
            if args.system_action == "status":
                cmd_status()
        else:
            cmd_status()
    elif args.command == "tokens":
        if args.tokens_action == "report":
            cmd_tokens_report()
    elif args.command == "config":
        if args.config_action == "validate":
            cmd_config_validate()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
