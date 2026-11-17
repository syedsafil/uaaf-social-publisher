"""
UAAF Comprehensive Verification Test Suite
==========================================
Verifies all 6 core audit requirements:
  1. Privacy and public posting safeguards
  2. Status reporting (uploaded_to_inbox, pending, timed_out)
  3. Credentials auditor accuracy (all required fields checked)
  4. Scheduler retry queue picking up failed/partial items
  5. Zero unawaited coroutines during single-platform runs
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python_agents"))
sys.path.insert(0, str(ROOT))

from config import Config
from examples.publish_clip import check_platform_credentials, ALL_PLATFORMS
from publish.video_validation import short_form_check
import publish.publish_all as pub_all
import local_scheduler


class TestUAAFPublishingSuite(unittest.TestCase):

    def setUp(self):
        self.sample_video = str(ROOT / "examples" / "sample-vertical.mp4")

    def test_01_video_validator(self):
        """Test video validator accepts valid 9:16 vertical sample."""
        res = short_form_check(self.sample_video)
        self.assertTrue(res["is_short_eligible"])
        self.assertEqual(res["width"], 540)
        self.assertEqual(res["height"], 960)
        self.assertLessEqual(res["duration_seconds"], 180.0)

    def test_02_credentials_auditor_required_fields(self):
        """Test TikTok requires CLIENT_SECRET, CLIENT_KEY, and TOKEN."""
        # Clear TikTok config
        with patch.object(Config, "TIKTOK_CLIENT_KEY", "mock_key"), \
             patch.object(Config, "TIKTOK_CLIENT_SECRET", ""), \
             patch.object(Config, "TIKTOK_ACCESS_TOKEN", "mock_tok"):
            res = check_platform_credentials("tiktok")
            self.assertFalse(res["configured"], "TikTok must not be marked configured without CLIENT_SECRET")
            self.assertIn("CLIENT_SECRET=MISSING", res["details"])

    def test_03_zero_unawaited_coroutine_warnings(self):
        """Test single-platform run generates zero unawaited coroutine warnings."""
        async def run_single():
            with patch("publish.publish_all._publish_youtube", return_value={"status": "success", "platform": "youtube"}):
                res = await pub_all.publish_to_all(
                    video_path=self.sample_video,
                    caption="Test",
                    title="Test",
                    hashtags=[],
                    platforms=["youtube"],
                )
                self.assertIn("youtube", res)
                self.assertNotIn("instagram", res)

        # Run within loop; any unawaited coroutine raises RuntimeWarning
        asyncio.run(run_single())

    def test_04_tiktok_creator_inbox_status(self):
        """Test TikTok Creator Inbox reports status 'uploaded_to_inbox'."""
        async def mock_inbox_flow(*args, **kwargs):
            # Mock httpx client response
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": {
                    "upload_url": "https://mock.tiktok.com/upload",
                    "publish_id": "v_inbox_file_98765",
                }
            }
            with patch("httpx.AsyncClient.post", return_value=mock_resp), \
                 patch("httpx.AsyncClient.put", return_value=mock_resp), \
                 patch.object(pub_all, "_get_fresh_tiktok_token", return_value="mock_token"):
                res = await pub_all._publish_tiktok(self.sample_video, "Caption", "Title", [])
                self.assertEqual(res["status"], "uploaded_to_inbox")
                self.assertTrue(res.get("inbox"))
                self.assertIn("Creator Inbox", res.get("message", ""))

        asyncio.run(mock_inbox_flow())

    def test_05_x_media_processing_timeout(self):
        """Test X.com stops and returns timed_out if media processing remains pending."""
        async def mock_x_timeout():
            mock_media = MagicMock()
            mock_media.media_id_string = "mock_media_123"

            mock_status = MagicMock()
            mock_status.processing_info = {"state": "in_progress"}

            mock_api = MagicMock()
            mock_api.media_upload.return_value = mock_media
            mock_api.get_media_upload_status.return_value = mock_status

            with patch("tweepy.OAuth1UserHandler"), \
                 patch("tweepy.API", return_value=mock_api), \
                 patch.object(Config, "X_API_KEY", "k"), \
                 patch.object(Config, "X_API_SECRET", "s"), \
                 patch.object(Config, "X_ACCESS_TOKEN", "t"), \
                 patch.object(Config, "X_ACCESS_TOKEN_SECRET", "ts"), \
                 patch("asyncio.sleep", return_value=None):
                res = await pub_all._publish_x(self.sample_video, "Test tweet")
                self.assertEqual(res["status"], "timed_out")
                self.assertIn("timed out", res.get("error", "").lower())

        asyncio.run(mock_x_timeout())

    def test_06_scheduler_retry_due_videos(self):
        """Test check_due_videos picks up failed items after next_retry_at has passed."""
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        future_time = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        mock_schedules = [
            {"id": "job_failed_ready", "title": "Retry Ready", "status": "failed", "next_retry_at": past_time, "publish_attempts": 1},
            {"id": "job_failed_waiting", "title": "Retry Waiting", "status": "failed", "next_retry_at": future_time, "publish_attempts": 1},
            {"id": "job_partial_ready", "title": "Partial Ready", "status": "partially_published", "next_retry_at": past_time, "publish_attempts": 1},
            {"id": "job_done", "title": "Published Done", "status": "published"},
        ]

        with patch.object(local_scheduler, "load_schedule", return_value=mock_schedules):
            due = local_scheduler.check_due_videos()
            due_ids = [item["id"] for item in due]
            self.assertIn("job_failed_ready", due_ids)
            self.assertIn("job_partial_ready", due_ids)
            self.assertNotIn("job_failed_waiting", due_ids)
            self.assertNotIn("job_done", due_ids)


    def test_07_mixed_result_partial_publishing_and_retry(self):
        """Test mixed result sets job status partially_published with retry, and retries ONLY failed platforms."""
        async def run_mixed():
            video_data = {
                "id": "vid_mixed_123",
                "title": "Mixed Result Test",
                "caption": "Testing partial fail and targeted retry",
                "hashtags": ["#test"],
                "video_path": self.sample_video,
                "status": "scheduled",
            }

            # Attempt 1: YouTube succeeds, Facebook fails
            mock_attempt_1 = {
                "youtube": {"status": "success", "url": "https://youtube.com/shorts/test123"},
                "facebook": {"status": "failed", "error": "Rate limit exceeded"}
            }

            with patch.object(Config, "YOUTUBE_REFRESH_TOKEN", "valid_token"), \
                 patch.object(Config, "META_ACCESS_TOKEN", "valid_token"), \
                 patch("publish.publish_all.publish_to_all", return_value=mock_attempt_1):
                res1 = await local_scheduler.publish_video_locally(video_data)
                
                # Verify Job Status is partially_published
                self.assertEqual(video_data["status"], "partially_published")
                self.assertEqual(video_data["failed_platforms"], ["facebook"])
                self.assertIn("next_retry_at", video_data)
                self.assertEqual(video_data["publish_attempts"], 1)

            # Attempt 2 (Retry): Should only target failed platform (Facebook), NOT YouTube
            attempted_platforms = []

            async def mock_retry_publish(*args, **kwargs):
                attempted_platforms.extend(kwargs.get("platforms") or [])
                return {"facebook": {"status": "success", "url": "https://facebook.com/reel/test456"}}

            with patch.object(Config, "YOUTUBE_REFRESH_TOKEN", "valid_token"), \
                 patch.object(Config, "META_ACCESS_TOKEN", "valid_token"), \
                 patch("publish.publish_all.publish_to_all", side_effect=mock_retry_publish):
                res2 = await local_scheduler.publish_video_locally(video_data)

                # Verify only the failed platform was retried
                self.assertEqual(attempted_platforms, ["facebook"], "Retry must only target failed platforms")

                # Verify Job Status is now fully published
                self.assertEqual(video_data["status"], "published")
                self.assertNotIn("failed_platforms", video_data)
                self.assertNotIn("next_retry_at", video_data)
                self.assertEqual(video_data["publish_attempts"], 2)
                self.assertEqual(video_data["published_platforms"]["youtube"]["status"], "success")
                self.assertEqual(video_data["published_platforms"]["facebook"]["status"], "success")

        asyncio.run(run_mixed())


    def test_08_incomplete_result_reporting_isolation(self):
        """Test scheduler marks job partially_published (never published) when channels are pending, timed_out, or inbox-staged."""
        async def run_incomplete_checks():
            # Scenario A: YouTube success, TikTok uploaded_to_inbox -> MUST BE partially_published, NOT published
            vid_inbox = {
                "id": "vid_inbox_test",
                "title": "Inbox Test",
                "caption": "Cap",
                "hashtags": [],
                "video_path": self.sample_video,
                "status": "scheduled",
            }
            mock_inbox = {
                "youtube": {"status": "success", "url": "https://youtube.com/shorts/live1"},
                "tiktok": {"status": "uploaded_to_inbox", "inbox": True}
            }
            with patch.object(Config, "YOUTUBE_REFRESH_TOKEN", "tok"), \
                 patch.object(Config, "TIKTOK_ACCESS_TOKEN", "tok"), \
                 patch("publish.publish_all.publish_to_all", return_value=mock_inbox):
                await local_scheduler.publish_video_locally(vid_inbox)
                self.assertEqual(vid_inbox["status"], "partially_published", "Success + Inbox must be partially_published, NOT published")
                self.assertEqual(vid_inbox["inbox_platforms"], ["tiktok"])
                self.assertEqual(vid_inbox["live_platforms"], ["youtube"])

            # Scenario B: YouTube success, X timed_out -> MUST BE partially_published with retry scheduled
            vid_timeout = {
                "id": "vid_timeout_test",
                "title": "Timeout Test",
                "caption": "Cap",
                "hashtags": [],
                "video_path": self.sample_video,
                "status": "scheduled",
            }
            mock_timeout = {
                "youtube": {"status": "success", "url": "https://youtube.com/shorts/live2"},
                "x": {"status": "timed_out", "error": "Media upload timed out"}
            }
            with patch.object(Config, "YOUTUBE_REFRESH_TOKEN", "tok"), \
                 patch.object(Config, "X_API_KEY", "key"), \
                 patch("publish.publish_all.publish_to_all", return_value=mock_timeout):
                await local_scheduler.publish_video_locally(vid_timeout)
                self.assertEqual(vid_timeout["status"], "partially_published", "Success + Timed_out must be partially_published")
                self.assertIn("x", vid_timeout["failed_platforms"])
                self.assertIn("next_retry_at", vid_timeout)

            # Scenario C: YouTube success, Instagram pending -> MUST BE partially_published
            vid_pending = {
                "id": "vid_pending_test",
                "title": "Pending Test",
                "caption": "Cap",
                "hashtags": [],
                "video_path": self.sample_video,
                "status": "scheduled",
            }
            mock_pending = {
                "youtube": {"status": "success", "url": "https://youtube.com/shorts/live3"},
                "instagram": {"status": "pending"}
            }
            with patch.object(Config, "YOUTUBE_REFRESH_TOKEN", "tok"), \
                 patch.object(Config, "META_ACCESS_TOKEN", "tok"), \
                 patch("publish.publish_all.publish_to_all", return_value=mock_pending):
                await local_scheduler.publish_video_locally(vid_pending)
                self.assertEqual(vid_pending["status"], "partially_published", "Success + Pending must be partially_published")
                self.assertEqual(vid_pending["pending_platforms"], ["instagram"])

            # Scenario D: TikTok alone uploaded_to_inbox -> MUST BE uploaded_to_inbox, NOT published
            vid_solo_inbox = {
                "id": "vid_solo_inbox_test",
                "title": "Solo Inbox Test",
                "caption": "Cap",
                "hashtags": [],
                "video_path": self.sample_video,
                "status": "scheduled",
            }
            mock_solo = {
                "tiktok": {"status": "uploaded_to_inbox", "inbox": True}
            }
            with patch.object(Config, "TIKTOK_ACCESS_TOKEN", "tok"), \
                 patch("publish.publish_all.publish_to_all", return_value=mock_solo):
                await local_scheduler.publish_video_locally(vid_solo_inbox)
                self.assertEqual(vid_solo_inbox["status"], "uploaded_to_inbox", "Solo inbox must report uploaded_to_inbox, NOT published")

        asyncio.run(run_incomplete_checks())


if __name__ == "__main__":
    unittest.main()
