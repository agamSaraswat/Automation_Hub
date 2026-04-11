import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services import automation


class ServicesAutomationTests(unittest.TestCase):
    def test_get_linkedin_status_detects_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            queue_dir = root / "output" / "linkedin" / "queue"
            queue_dir.mkdir(parents=True)
            today = automation.date.today().isoformat()
            (queue_dir / f"{today}.md").write_text("draft", encoding="utf-8")

            with patch.object(automation, "REPO_ROOT", root), patch.dict(os.environ, {}, clear=False):
                status = automation.get_linkedin_status()

            self.assertEqual(status["status"], "In queue (review needed)")
            self.assertTrue(status["queue_file_exists"])
            self.assertFalse(status["posted_file_exists"])

    @patch("src.jobs.claude_resume_tailoring.save_tailored_resume")
    @patch(
        "src.jobs.claude_resume_tailoring.tailor_resume_for_job",
        return_value={"job_id": "job-1", "tailored_resume": "resume"},
    )
    @patch("src.jobs.claude_job_discovery.queue_discovered_jobs", return_value=2)
    @patch(
        "src.jobs.claude_job_discovery.run_job_discovery",
        return_value={
            "jobs": [
                {"unique_id": "job-1", "title": "Role 1", "jd_snippet": "desc"},
                {"unique_id": "job-2", "title": "Role 2", "jd_snippet": "desc"},
            ],
            "run_metadata": {"tokens_used": 100, "after_dedup": 2},
        },
    )
    @patch("src.jobs.deduplicator.get_todays_queue", return_value=[{"id": 1}, {"id": 2}])
    @patch("src.jobs.deduplicator.get_stats", return_value={"total_jobs": 10, "today_queued": 2, "by_status": {"queued": 2}})
    def test_run_jobs_pipeline_returns_structured_output(
        self,
        mock_stats,
        mock_queue,
        mock_run_discovery,
        mock_queue_discovered,
        mock_tailor,
        mock_save_tailored,
    ):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            result = automation.run_jobs_pipeline()

        self.assertEqual(result["scraped_new_jobs"], 2)
        self.assertEqual(result["tailored_jobs"], 2)
        self.assertEqual(result["queue_size_today"], 2)
        self.assertIn("stats", result)

    @patch("src.briefing.morning_briefing.generate_briefing", return_value="hello")
    @patch("src.messaging.telegram_bot.send_message_sync")
    def test_run_briefing_now_can_send_telegram(self, mock_send, mock_generate):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "y"}, clear=False):
            result = automation.run_briefing_now(send_to_telegram=True)

        self.assertEqual(result["briefing"], "hello")
        self.assertTrue(result["sent_to_telegram"])
        mock_send.assert_called_once_with("hello")

    @patch(
        "src.messaging.gmail_triage_v2.run_triage_v2",
        return_value={
            "summary_text": "summary",
            "classified_json": "[]",
            "decision_needed": False,
            "urgent_count": 0,
            "normal_count": 0,
        },
    )
    @patch("src.messaging.telegram_bot.send_message_sync")
    def test_run_gmail_triage_now_can_skip_telegram(self, mock_send, mock_triage):
        result = automation.run_gmail_triage_now(send_to_telegram=False)

        self.assertEqual(result["summary"], "summary")
        self.assertFalse(result["sent_to_telegram"])
        mock_send.assert_not_called()

    @patch("src.jobs.deduplicator.init_db")
    @patch("src.jobs.deduplicator.get_stats", return_value={"total_jobs": 1, "today_queued": 1, "by_status": {"queued": 1}})
    @patch("src.services.automation.get_environment_status", return_value={"ANTHROPIC_API_KEY": {"set": True, "required": True, "description": "x"}})
    @patch("src.services.automation.get_linkedin_status", return_value={"status": "Not generated"})
    def test_get_system_status_aggregates_sections(self, mock_linkedin, mock_env, mock_stats, mock_init_db):
        status = automation.get_system_status()

        self.assertIn("date", status)
        self.assertIn("environment", status)
        self.assertIn("jobs", status)
        self.assertIn("linkedin", status)

    @patch("src.jobs.deduplicator.init_db")
    @patch("src.jobs.deduplicator.get_todays_queue", return_value=[{"id": 1}])
    def test_get_jobs_queue(self, mock_queue, mock_init_db):
        queue = automation.get_jobs_queue(limit=20)
        self.assertEqual(len(queue), 1)
        mock_init_db.assert_called_once()

    @patch("src.jobs.deduplicator.init_db")
    @patch("src.jobs.deduplicator.get_stats", return_value={"total_jobs": 2, "today_queued": 1, "by_status": {"queued": 1}})
    def test_get_jobs_stats(self, mock_stats, mock_init_db):
        stats = automation.get_jobs_stats()
        self.assertEqual(stats["total_jobs"], 2)
        mock_init_db.assert_called_once()


if __name__ == "__main__":
    unittest.main()
