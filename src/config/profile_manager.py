"""
User Profile Configuration System

Allows swapping user identity/configuration without rebuilding code.
Supports multiple profiles (e.g., agam_profile.yaml, soumyabrata_profile.yaml).

Structure:
  config/
    profiles/
      agam.yaml              (example profile)
      soumyabrata.yaml       (your profile)
    profile_schema.yaml      (required fields)
    active_profile.txt       (current profile name)

Usage:
  # Swap profiles
  python -m src.config.profile_manager --set soumyabrata

  # Verify loaded profile
  python -m src.config.profile_manager --verify

  # Show current profile
  python -m src.config.profile_manager --show
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES_DIR = REPO_ROOT / "config" / "profiles"
ACTIVE_PROFILE_FILE = REPO_ROOT / "config" / "active_profile.txt"


def get_profiles_dir() -> Path:
    """Get profiles directory, create if needed."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def get_active_profile_name() -> str:
    """Get currently active profile name (default: agam)."""
    try:
        if ACTIVE_PROFILE_FILE.exists():
            with open(ACTIVE_PROFILE_FILE, "r", encoding="utf-8") as f:
                name = f.read().strip()
                if name:
                    return name
    except Exception as exc:
        logger.warning(f"Error reading active profile: {exc}")

    return "agam"  # Default


def set_active_profile(profile_name: str) -> bool:
    """Set active profile."""
    try:
        # Verify profile exists
        profile_path = get_profiles_dir() / f"{profile_name}.yaml"
        if not profile_path.exists():
            logger.error(f"Profile not found: {profile_path}")
            return False

        # Write active profile
        with open(ACTIVE_PROFILE_FILE, "w", encoding="utf-8") as f:
            f.write(profile_name)

        logger.info(f"Active profile set to: {profile_name}")
        return True
    except Exception as exc:
        logger.error(f"Error setting profile: {exc}")
        return False


def load_profile(profile_name: Optional[str] = None) -> dict[str, Any]:
    """Load user profile configuration."""
    if profile_name is None:
        profile_name = get_active_profile_name()

    profile_path = get_profiles_dir() / f"{profile_name}.yaml"

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f)

        logger.info(f"Loaded profile: {profile_name}")
        return profile or {}
    except FileNotFoundError:
        logger.error(f"Profile not found: {profile_path}")
        return {}
    except Exception as exc:
        logger.error(f"Error loading profile: {exc}")
        return {}


def validate_profile(profile: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate profile has required fields."""
    required_fields = [
        "name",
        "email",
        "phone",
        "location",
        "master_resume_path",
        "linkedin_profile",
        "job_preferences",
    ]

    errors = []
    for field in required_fields:
        if field not in profile:
            errors.append(f"Missing required field: {field}")

    job_prefs = profile.get("job_preferences", {})
    required_job_fields = ["target_roles", "target_keywords", "locations"]
    for field in required_job_fields:
        if field not in job_prefs:
            errors.append(f"Missing job_preferences.{field}")

    return len(errors) == 0, errors


def get_profile_field(field_path: str, profile: Optional[dict[str, Any]] = None) -> Any:
    """Get field from profile using dot notation (e.g., 'job_preferences.target_roles')."""
    if profile is None:
        profile = load_profile()

    parts = field_path.split(".")
    current = profile

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def merge_profile_with_config(
    profile: dict[str, Any],
    job_search_config: dict[str, Any],
) -> dict[str, Any]:
    """Merge user profile into job search config."""
    merged = job_search_config.copy()

    # Override with profile preferences
    job_prefs = profile.get("job_preferences", {})

    # Update job discovery config
    if "job_discovery" in merged:
        merged["job_discovery"]["target_roles"] = job_prefs.get("target_roles", [])
        merged["job_discovery"]["target_keywords"] = job_prefs.get("target_keywords", [])
        merged["job_discovery"]["exclude_keywords"] = job_prefs.get("exclude_keywords", [])
        merged["job_discovery"]["locations"] = job_prefs.get("locations", [])

    # Update resume tailoring
    if "resume_tailoring" in merged:
        merged["resume_tailoring"]["master_resume_path"] = profile.get("master_resume_path", "")

    return merged


# ── CLI Management ────────────────────────────────────────────

def cmd_set_profile(profile_name: str):
    """CLI: Set active profile."""
    if set_active_profile(profile_name):
        print(f"✅ Profile set to: {profile_name}")
    else:
        print(f"❌ Failed to set profile: {profile_name}")
        sys.exit(1)


def cmd_show_profile():
    """CLI: Show current profile."""
    profile_name = get_active_profile_name()
    profile = load_profile(profile_name)

    print(f"\n📋 Active Profile: {profile_name}\n")

    if not profile:
        print("  (empty)")
        return

    # Show basic info
    print(f"  Name: {profile.get('name', '?')}")
    print(f"  Email: {profile.get('email', '?')}")
    print(f"  Phone: {profile.get('phone', '?')}")
    print(f"  Location: {profile.get('location', '?')}")
    print(f"  LinkedIn: {profile.get('linkedin_profile', '?')}")

    # Show job preferences
    job_prefs = profile.get("job_preferences", {})
    print(f"\n  📊 Job Preferences:")
    print(f"    Roles: {', '.join(job_prefs.get('target_roles', [])[:3])}")
    print(f"    Keywords: {', '.join(job_prefs.get('target_keywords', [])[:3])}")
    print(f"    Locations: {', '.join(job_prefs.get('locations', [])[:3])}")

    print()


def cmd_verify_profile():
    """CLI: Verify profile integrity."""
    profile_name = get_active_profile_name()
    profile = load_profile(profile_name)

    valid, errors = validate_profile(profile)

    print(f"\n🔍 Verifying Profile: {profile_name}\n")

    if valid:
        print("  ✅ Profile is valid")
    else:
        print("  ❌ Profile has errors:")
        for error in errors:
            print(f"    • {error}")
        sys.exit(1)

    print()


def cmd_list_profiles():
    """CLI: List available profiles."""
    profiles_dir = get_profiles_dir()
    profiles = list(profiles_dir.glob("*.yaml"))

    active = get_active_profile_name()

    print(f"\n📂 Available Profiles ({len(profiles)}):\n")

    for profile_path in sorted(profiles):
        name = profile_path.stem
        marker = "✅" if name == active else "  "
        print(f"  {marker} {name}")

    print()


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="User Profile Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.config.profile_manager --set soumyabrata
  python -m src.config.profile_manager --show
  python -m src.config.profile_manager --verify
  python -m src.config.profile_manager --list
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", metavar="NAME", help="Set active profile")
    group.add_argument("--show", action="store_true", help="Show current profile")
    group.add_argument("--verify", action="store_true", help="Verify profile integrity")
    group.add_argument("--list", action="store_true", help="List all profiles")

    args = parser.parse_args()

    if args.set:
        cmd_set_profile(args.set)
    elif args.show:
        cmd_show_profile()
    elif args.verify:
        cmd_verify_profile()
    elif args.list:
        cmd_list_profiles()
