# UAAF: Universal Autonomous Automation Framework

Autonomous multi-platform video publishing engine and audience engagement pipeline.

## Overview
UAAF orchestrates scheduled video publication across major social platforms (Instagram Reels, TikTok, YouTube Shorts, Facebook Reels, and X) while maintaining an automated comment-to-DM conversational workflow.

## Key Capabilities
- **Multi-Platform Dispatcher**: Unified publication pipeline with platform-specific chunked video uploads and rate-limit compliance.
- **Token Lifecycle Management**: Autonomous OAuth token refresh mechanism preventing execution interruption during token expiration cycles.
- **Engagement Worker**: Real-time webhook and polling engine matching viewer comments to asset keywords for automated direct messaging.
- **Modular Architecture**: Isolated agents for media rendering, asset metadata generation, and delivery tracking.

## System Components
- python_agents/publish/: Handlers for Meta Graph API, TikTok Content Posting API, YouTube Data v3, and X API.
- python_agents/webhook/: Comment listener and DM dispatcher logic.
- python_agents/local_scheduler.py: Local cron-loop engine with retry persistence.
- python_agents/config.py: Centralized environment configuration loader.

## Quick Start
1. Clone the repository:
   `ash
   git clone https://github.com/syedwebsite1/uaaf-social-publisher.git
   cd uaaf-social-publisher
   `
2. Set up virtual environment and dependencies:
   `ash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   `
3. Configure environment credentials:
   `ash
   cp .env.example .env
   `
4. Run the orchestration engine:
   `ash
   python python_agents/local_scheduler.py
   `

## License
MIT License.
