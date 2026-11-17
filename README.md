<p>
  <img src="media/uaaf-hero.jpg" alt="UAAF Social Publisher. Publish short videos from your own setup." width="100%">
</p>

# UAAF Social Publisher

A self-hosted Python framework for publishing vertical short-form video across **YouTube Shorts, Instagram Reels, Facebook Reels, TikTok, and X (Twitter)**. Validate your video locally, verify credentials, and publish via native APIs.

<p align="center">
  <a href="https://github.com/syedsafil/uaaf-social-publisher/releases/download/v0.1.1/uaaf-starter.zip"><img src="https://img.shields.io/badge/Download_Starter_ZIP-CBB5FF?style=for-the-badge&amp;logo=github&amp;logoColor=17141F" height="40" alt="Download Starter ZIP"></a>
</p>

[Video Check](#1-video-check) · [Credentials Audit](#2-credentials-audit) · [Publish Across 5 Platforms](#3-publish-across-5-platforms) · [Channel Setup](#4-channel-setup-guides) · [Platform Adapters](#5-platform-adapters) · [Test Suite](#6-test-suite) · [Issues](https://github.com/syedsafil/uaaf-social-publisher/issues)

---

## 1. Video Check

Before uploading to any social platform, validate that your video meets the vertical 9:16 aspect ratio and duration criteria. The local check uses the Python standard library and `ffprobe`:

```sh
git clone https://github.com/syedsafil/uaaf-social-publisher.git
cd uaaf-social-publisher
python -m examples.check_clip examples/sample-vertical.mp4
```

Output:
```json
{
  "width": 540,
  "height": 960,
  "duration_seconds": 3.0,
  "is_short_eligible": true,
  "problems": []
}
```

---

## 2. Credentials Audit

Check your `.env` configuration across all 5 social destinations in one command:

```sh
# Offline syntax check
python -m examples.check_credentials

# Live online API connectivity check (tests tokens against live APIs)
python -m examples.check_credentials --online
```

This inspects your local environment and provides immediate status for each platform along with setup hints for any missing keys.

---

## 3. Publish Across 5 Platforms

Use the unified CLI `examples/publish_clip` to publish to any individual platform or all platforms simultaneously.

### Offline Dry-Run (All Platforms)
Validate video geometry and credentials without sending any network upload requests:

```sh
python -m examples.publish_clip examples/sample-vertical.mp4 --platform all --dry-run
```

### Privacy & Public Posting Safety
* **Safe Defaults:** Private testing is the default (`--privacy private`).
* **Privacy Constraints:** YouTube Shorts supports `private`. TikTok supports `private` (mapped to `SELF_ONLY`).
* **Public Posting Safeguards:** Instagram, Facebook, and X APIs do not support private video uploads. To prevent accidental public leakage during developer testing, these platforms are automatically skipped in `--privacy private` mode unless `--allow-public` is explicitly provided.

### Single-Platform Publishing Commands

* **YouTube Shorts** (Private test upload):
  ```sh
  python -m examples.publish_clip examples/sample-vertical.mp4 --platform youtube --privacy private
  ```

* **TikTok** (Private upload via `SELF_ONLY` or Creator Inbox fallback):
  ```sh
  python -m examples.publish_clip examples/sample-vertical.mp4 --platform tiktok --privacy private
  ```

* **Instagram Reels** (Direct binary rupload via Meta Graph API v20):
  ```sh
  python -m examples.publish_clip examples/sample-vertical.mp4 --platform instagram --allow-public
  ```

* **Facebook Reels** (Page Video API chunked container):
  ```sh
  python -m examples.publish_clip examples/sample-vertical.mp4 --platform facebook --allow-public
  ```

* **X (Twitter)** (Media Upload API v1.1 chunked + Tweet creation v2):
  ```sh
  python -m examples.publish_clip examples/sample-vertical.mp4 --platform x --allow-public
  ```

### Multi-Platform Simultaneous Dispatch
Publish your clip to all configured platforms in parallel:

```sh
python -m examples.publish_clip examples/sample-vertical.mp4 --platform all --allow-public
```

Terminal Output *(Example Output)*:
```text
=================================================================
UAAF MULTI-PLATFORM SOCIAL PUBLISHER
=================================================================

[1/3] Validating video format: sample-vertical.mp4
   Dimensions: 540x960 (Vertical 9:16: YES)
   Duration:   3.0s (Shorts/Reels limit: <= 180s)
   Eligible:   True

[2/3] Checking credentials for target platform(s): youtube, instagram, facebook, tiktok, x
   [CONFIGURED]   YOUTUBE    - CLIENT_ID=SET, CLIENT_SECRET=SET, REFRESH_TOKEN=SET
   [CONFIGURED]   INSTAGRAM  - META_ACCESS_TOKEN=SET, IG_ACCOUNT_ID=SET
   [CONFIGURED]   FACEBOOK   - META_ACCESS_TOKEN=SET, FB_PAGE_ID=SET
   [CONFIGURED]   TIKTOK     - CLIENT_KEY=SET, CLIENT_SECRET=SET, TOKEN=SET
   [CONFIGURED]   X          - API_KEY=SET, API_SECRET=SET, ACCESS_TOKEN=SET, ACCESS_SECRET=SET

[3/3] Initiating live publication...

=================================================================
PUBLICATION RESULTS (12.4s)
=================================================================
   [SUCCESS] YOUTUBE    -> https://www.youtube.com/shorts/bjLGjKSNwJg
   [SUCCESS] INSTAGRAM  -> https://www.instagram.com/reel/De9gFEnElFt/
   [SUCCESS] FACEBOOK   -> https://facebook.com/reel/1128395313101108/
   [INBOX]   TIKTOK     -> https://www.tiktok.com/@your_channel (Uploaded to Creator Inbox)
   [SUCCESS] X          -> https://x.com/user/status/17891238910
=================================================================
```

---

## 4. Channel Setup Guides

Copy `.env.example` to `.env` and configure credentials for the channels you want to use:

### YouTube Shorts
1. Enable **YouTube Data API v3** in [Google Cloud Console](https://console.cloud.google.com/).
2. Create an **OAuth 2.0 Client ID** (Application type: *Desktop app*).
3. Set `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in `.env`.
4. Run the 1-click token generator:
   ```sh
   python python_agents/utils/youtube_auth.py
   ```
   *(Your browser will open for authentication and automatically save `YOUTUBE_REFRESH_TOKEN` to `.env`)*.

### TikTok
1. Register an app on [TikTok Developer Portal](https://developers.tiktok.com/).
2. Add `video.upload` and `video.publish` scopes.
3. Set `TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` in `.env`.
4. Run the local OAuth callback server:
   ```sh
   python python_agents/utils/tiktok_auth.py
   ```

### Meta (Instagram & Facebook Reels)
1. In the [Meta for Developers Portal](https://developers.facebook.com/), create a Business app.
2. Generate a System User Access Token with `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`.
3. Set in `.env`:
   ```env
   META_ACCESS_TOKEN="your_token"
   META_IG_BUSINESS_ACCOUNT_ID="your_instagram_business_account_id"
   META_FB_PAGE_ID="your_facebook_page_id"
   ```

### X.com (Twitter)
1. In the [X Developer Portal](https://developer.x.com/), generate OAuth 1.0a User Context keys (Read and Write) and API v2 tokens.
2. Set in `.env`:
   ```env
   X_API_KEY="your_api_key"
   X_API_SECRET="your_api_secret"
   X_ACCESS_TOKEN="your_access_token"
   X_ACCESS_TOKEN_SECRET="your_access_token_secret"
   ```

---

## 5. Platform Adapters

| Destination | Pipeline Architecture | Verification Status |
| :--- | :--- | :--- |
| **YouTube Shorts** | Chunked Resumable Upload via Data API v3 | [Verified Live Short](https://www.youtube.com/shorts/bjLGjKSNwJg) |
| **Instagram Reels** | Direct Binary Rupload via Meta Graph API v20 | Implemented · Live test pending credentials |
| **Facebook Reels** | Two-Phase Video Reels Upload via Page Video API | Implemented · Live test pending credentials |
| **TikTok** | Direct Post & Creator Inbox Flow (API v2) | Implemented · Live test pending credentials |
| **X** | Media Upload API v1.1 (chunked) + Tweet Creation API v2 | Implemented · Live test pending credentials |

See [python_agents/publish/publish_all.py](python_agents/publish/publish_all.py) and [.env.example](.env.example) for entry points.

---

## 6. Test Suite

Run the automated verification suite to test video geometry validation, credentials auditing, privacy constraints, status reporting, and scheduler retry queues:

```sh
python -m unittest tests/test_publishing_suite.py -v
```

---

## Share Feedback

If you run the local validator or test publishing to any channel, share your environment details and feedback in a [GitHub Issue](https://github.com/syedsafil/uaaf-social-publisher/issues).
