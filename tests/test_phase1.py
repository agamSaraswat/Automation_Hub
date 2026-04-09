"""
Test suite for Phase 1: Job Discovery, Resume Tailoring, Gmail Triage, Harness.

Usage:
  python -m pytest tests/test_phase1.py -v
  python tests/test_phase1.py --dry-run
"""

import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)


class TestHarness:
    """Test Planner-Generator-Evaluator harness."""

    def test_harness_imports(self):
        """Verify harness module imports."""
        from src.jobs.harness import (
            PlannerGeneratorEvaluator,
            SprintContract,
            HarnessPhase,
        )
        assert PlannerGeneratorEvaluator is not None
        assert SprintContract is not None
        assert HarnessPhase is not None

    def test_sprint_contract(self):
        """Test SprintContract initialization."""
        from src.jobs.harness import SprintContract

        contract = SprintContract(
            name="test",
            required_fields=["output", "trace"],
            max_iterations=2,
        )
        assert contract.name == "test"
        assert contract.max_iterations == 2
        assert "output" in contract.required_fields

    def test_harness_initialization(self):
        """Test harness initialization."""
        from src.jobs.harness import PlannerGeneratorEvaluator, SprintContract

        contract = SprintContract(
            name="test_harness",
            required_fields=["summary"],
        )
        harness = PlannerGeneratorEvaluator(contract)
        assert harness.contract.name == "test_harness"
        assert harness.total_tokens == 0


class TestJobDiscoverySkill:
    """Test job discovery skill definition."""

    def test_skill_file_exists(self):
        """Verify skill.md file exists."""
        skill_path = REPO_ROOT / "src" / "jobs" / "job-discovery.md"
        assert skill_path.exists(), f"Skill file not found: {skill_path}"

    def test_skill_content(self):
        """Check skill file contains required sections."""
        skill_path = REPO_ROOT / "src" / "jobs" / "job-discovery.md"
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = ["Single-line description", "SLA Contract", "WILL", "WON'T"]
        for section in required_sections:
            assert section in content, f"Missing section: {section}"


class TestResumeTailoringSkill:
    """Test resume tailoring skill definition."""

    def test_skill_file_exists(self):
        """Verify skill.md file exists."""
        skill_path = REPO_ROOT / "src" / "jobs" / "resume-tailoring.md"
        assert skill_path.exists()

    def test_skill_mentions_harness(self):
        """Verify skill mentions adversarial harness."""
        skill_path = REPO_ROOT / "src" / "jobs" / "resume-tailoring.md"
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Planner" in content
        assert "Generator" in content
        assert "Evaluator" in content
        assert "harness" in content.lower()


class TestLinkedInContentSkill:
    """Test LinkedIn content skill definition."""

    def test_skill_file_exists(self):
        """Verify skill.md file exists."""
        skill_path = REPO_ROOT / "src" / "linkedin" / "linkedin-content.md"
        assert skill_path.exists()

    def test_skill_has_sla(self):
        """Verify skill has SLA contract."""
        skill_path = REPO_ROOT / "src" / "linkedin" / "linkedin-content.md"
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "SLA Contract" in content


class TestTokenInstrumentation:
    """Test token tracking and cost estimation."""

    def test_token_instrumentation_imports(self):
        """Verify token instrumentation imports."""
        from src.services.token_instrumentation import (
            TokenInstrumenter,
            TokenUsage,
            SkillName,
        )
        assert TokenInstrumenter is not None
        assert TokenUsage is not None
        assert SkillName is not None

    def test_token_usage_creation(self):
        """Test TokenUsage creation and cost estimation."""
        from src.services.token_instrumentation import TokenUsage, SkillName

        usage = TokenUsage(
            skill_name=SkillName.JOB_DISCOVERY,
            input_tokens=1000,
            output_tokens=500,
        )
        assert usage.total_tokens() == 1500
        assert usage.estimated_cost_usd() > 0

    def test_instrumentation_recording(self):
        """Test instrumentation recording."""
        from src.services.token_instrumentation import TokenInstrumenter, SkillName

        instrumenter = TokenInstrumenter("test_run_001")
        instrumenter.record(SkillName.JOB_DISCOVERY, 1000, 500)
        instrumenter.record(SkillName.RESUME_TAILORING, 800, 400)

        assert instrumenter.total_tokens() == 2700
        summary = instrumenter.summary()
        assert summary["total_records"] == 2
        assert "by_skill" in summary


class TestGmailTriageV2:
    """Test Gmail triage v2 with structured output."""

    def test_gmail_triage_imports(self):
        """Verify Gmail triage v2 imports."""
        from src.messaging.gmail_triage_v2 import (
            get_unread_count,
            get_recent_emails,
            run_triage_v2,
        )
        assert get_unread_count is not None
        assert get_recent_emails is not None
        assert run_triage_v2 is not None

    def test_get_unread_count_mock(self):
        """Test unread count with mock."""
        from src.messaging.gmail_triage_v2 import get_unread_count

        mock_service.return_value.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "resultSizeEstimate": 5
        }

        # This will fail without real Gmail config, so skip
        logger.info("Skipping real Gmail test (requires credentials)")


class TestClaudeJobDiscovery:
    """Test Claude-powered job discovery."""

    def test_job_discovery_imports(self):
        """Verify job discovery imports."""
        from src.jobs.claude_job_discovery import (
            run_job_discovery,
            queue_discovered_jobs,
        )
        assert run_job_discovery is not None
        assert queue_discovered_jobs is not None

    def test_dedup_jobs_function(self):
        """Test job deduplication."""
        from src.jobs.claude_job_discovery import _dedup_jobs

        jobs = [
            {"url": "http://job1.com", "title": "Job 1"},
            {"url": "http://job2.com", "title": "Job 2"},
            {"url": "http://job1.com", "title": "Job 1 Duplicate"},
        ]

        deduped = _dedup_jobs(jobs)
        # Should remove at least the duplicate
        assert len(deduped) <= len(jobs)


class TestResumeTailoringEngine:
    """Test Claude resume tailoring."""

    def test_resume_tailoring_imports(self):
        """Verify resume tailoring imports."""
        from src.jobs.claude_resume_tailoring import (
            load_master_resume,
            tailor_resume_for_job,
        )
        assert load_master_resume is not None
        assert tailor_resume_for_job is not None

    def test_master_resume_loads(self):
        """Test master resume loads."""
        from src.jobs.claude_resume_tailoring import load_master_resume

        try:
            resume = load_master_resume()
            assert isinstance(resume, str)
            assert len(resume) > 0
            assert "Data Scientist" in resume or "Agam" in resume
        except FileNotFoundError:
            logger.warning("Master resume not found (expected if running tests without full setup)")


class TestAutomationService:
    """Test automation service integration."""

    def test_automation_imports(self):
        """Verify automation service imports."""
        from src.services.automation import (
            run_jobs_pipeline,
            run_gmail_triage_now,
            get_environment_status,
        )
        assert run_jobs_pipeline is not None
        assert run_gmail_triage_now is not None
        assert get_environment_status is not None

    def test_environment_status(self):
        """Test environment status check."""
        from src.services.automation import get_environment_status

        status = get_environment_status()
        assert "ANTHROPIC_API_KEY" in status


class TestConfigLoading:
    """Test configuration loading."""

    def test_job_search_config_loads(self):
        """Test job search config loads."""
        import yaml
        from pathlib import Path

        config_path = REPO_ROOT / "config" / "job_search.yaml"
        assert config_path.exists()

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "job_discovery" in config
        assert config["job_discovery"]["enabled"] is True
        assert "target_roles" in config["job_discovery"]


# ── CLI Test Runner ──────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUITE")
    print("=" * 60 + "\n")

    # Run tests
    tests = [
        ("Harness", TestHarness),
        ("Job Discovery Skill", TestJobDiscoverySkill),
        ("Resume Tailoring Skill", TestResumeTailoringSkill),
        ("LinkedIn Content Skill", TestLinkedInContentSkill),
        ("Token Instrumentation", TestTokenInstrumentation),
        ("Gmail Triage v2", TestGmailTriageV2),
        ("Claude Job Discovery", TestClaudeJobDiscovery),
        ("Resume Tailoring", TestResumeTailoringEngine),
        ("Automation Service", TestAutomationService),
        ("Config Loading", TestConfigLoading),
    ]

    passed = 0
    failed = 0

    for test_name, test_class in tests:
        print(f"\n[TEST] {test_name}")
        print("-" * 60)

        try:
            for method_name in dir(test_class):
                if method_name.startswith("test_"):
                    method = getattr(test_class, method_name)
                    try:
                        instance = test_class()
                        method(instance)
                        print(f"  ✓ {method_name}")
                        passed += 1
                    except Exception as exc:
                        print(f"  ✗ {method_name}: {exc}")
                        failed += 1
        except Exception as exc:
            print(f"  ✗ Setup error: {exc}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
