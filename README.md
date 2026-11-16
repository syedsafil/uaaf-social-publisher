<p>
  <img src="media/uaaf-hero.jpg" alt="UAAF Social Publisher. Publish short videos from your own setup." width="100%">
</p>

# UAAF Social Publisher

A self-hosted Python project for publishing short videos to the social accounts you connect. Start by checking a clip locally, then explore the publishing adapters for your channels.

<p align="center">
  <a href="https://github.com/syedsafil/uaaf-social-publisher/releases/download/v0.1.0/uaaf-starter.zip"><img src="https://img.shields.io/badge/Download_Starter_ZIP-CBB5FF?style=for-the-badge&amp;logo=github&amp;logoColor=17141F" height="40" alt="Download Starter ZIP"></a>
</p>

[Try the video check](#try-the-video-check) · [Publish your first YouTube Short](#publish-your-first-youtube-short) · [See the workflow](#see-the-workflow) · [Publishing adapters](#publishing-adapters) · [Share feedback](https://github.com/syedsafil/uaaf-social-publisher/issues)

## Try the video check

You need Git, Python, and `ffprobe` from FFmpeg on your PATH. The local check uses the Python standard library and runs without social account credentials.

```sh
git clone https://github.com/syedsafil/uaaf-social-publisher.git
cd uaaf-social-publisher
python -m examples.check_clip examples/sample-vertical.mp4
```

The sample returns `540 × 960`, `3.0` seconds, and `"is_short_eligible": true`. This check evaluates the frame shape and duration for YouTube Shorts. It runs locally and uploads nothing.

## Publish your first YouTube Short

Any developer can follow these reproducible steps to publish a test clip as a private YouTube Short using the YouTube Data API v3.

### 1. Account setup
1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the **YouTube Data API v3**.
2. Go to **APIs & Services > Credentials** and create an **OAuth 2.0 Client ID** (Application type: *Desktop app*).
3. Copy `.env.example` to `.env` and fill in your credentials:
   ```env
   YOUTUBE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
   YOUTUBE_CLIENT_SECRET="your_client_secret"
   ```
4. Authorize your channel locally by running the token helper:
   ```sh
   python python_agents/utils/youtube_auth.py
   ```
   This opens your browser to grant permissions and automatically appends your `YOUTUBE_REFRESH_TOKEN` to `.env`.

### 2. Run the publisher command

Publish the included vertical sample clip with `--privacy private` (safe for testing without public exposure):

```sh
python -m examples.publish_youtube_short examples/sample-vertical.mp4 --privacy private
```

To test clip geometry and configuration without sending an upload request, append `--dry-run`:
```sh
python -m examples.publish_youtube_short examples/sample-vertical.mp4 --dry-run
```

### 3. Expected output

```text
1. Validating clip specifications: sample-vertical.mp4
   - Dimensions: 540x960
   - Duration:   3.0s
   - Eligible:   True

2. Authenticating with YouTube Data API v3...
   - OAuth 2.0 access token successfully refreshed.

3. Initiating upload session (privacy: private)...
4. Uploading video data (16.7 KB)...

==================================================
PUBLICATION COMPLETED
==================================================
{
  "status": "success",
  "platform": "youtube",
  "video_id": "bjLGjKSNwJg",
  "url": "https://www.youtube.com/shorts/bjLGjKSNwJg",
  "privacy": "private",
  "is_short": true
}

Live Short URL: https://www.youtube.com/shorts/bjLGjKSNwJg
```

View an actual verified post published with this pipeline: [YouTube Short (Live Post)](https://www.youtube.com/shorts/bjLGjKSNwJg).

## See the workflow

<p>
  <img src="media/video-check.gif" alt="Replay of the local video check. The vertical sample passes and a landscape clip is flagged." width="100%">
</p>

Replay based on actual output from the local validator. [View the static result](media/video-check.png) · [Download the sample clip](examples/sample-vertical.mp4)

The publishing code accepts a clip and its post text, dispatches to the selected adapters, and returns each platform's result. A scheduler and comment handlers are also in the repository.

## Publishing adapters

| Destination | Code in this repository | Verification |
| --- | --- | --- |
| YouTube Shorts | Video uploading adapter and local frame/duration check | [Live publish verified](https://www.youtube.com/shorts/bjLGjKSNwJg) · Data API v3 |
| Instagram Reels | Video publishing adapter | [Live publish verified](https://www.instagram.com/reel/De9gFEnElFt/) · Meta Graph API v20 |
| Facebook Reels | Video publishing adapter | [Live publish verified](https://facebook.com/reel/1128395313101108/) · Page Video API |
| TikTok | Content posting adapter (chunked) | [Adapter verified](https://www.tiktok.com) · Content Posting API v2 |
| X | Video publishing adapter | [Adapter verified](https://x.com) · Media Upload API v2 |

See the [publishing code](python_agents/publish/publish_all.py) and the [environment template](.env.example) for integration entry points. Publishing requires the appropriate accounts, credentials and API access for each channel. Keep personal credentials out of issues and screenshots.

## Share feedback

If you try the local check or YouTube Short publisher, share your OS, Python version and the output in a [GitHub issue](https://github.com/syedsafil/uaaf-social-publisher/issues). Include the platform and a redacted error if you're reporting an adapter issue.
