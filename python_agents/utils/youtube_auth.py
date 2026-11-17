"""
YOUTUBE OAUTH 2.0 TOKEN GENERATOR — 100% UNIVERSAL AUTHENTICATION
═══════════════════════════════════════════════════════════════
Chalaayein: python python_agents/utils/youtube_auth.py
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from google_auth_oauthlib.flow import InstalledAppFlow

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

def main():
    if not Config.YOUTUBE_CLIENT_ID or not Config.YOUTUBE_CLIENT_SECRET:
        print("[!] Error: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env")
        return

    print("\n[+] YouTube OAuth 2.0 Token Generator")
    print("=" * 60)

    # 1. Try local server flow with port=0 (auto port selection)
    client_config = {
        "installed": {
            "client_id": Config.YOUTUBE_CLIENT_ID,
            "client_secret": Config.YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost", "http://localhost:8080/"],
        }
    }

    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        print("\n[+] Direct Authorization URL:\n" + auth_url, flush=True)
        print("\n[+] Opening browser automatically... Please approve permissions.", flush=True)
        creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
    except Exception as e:
        print(f"\n[!] Local redirect error: {e}")
        print("\n[>] ALTERNATIVE: Google OAuth Playground Method (Guaranteed 100% Work):")
        print("1. Open https://developers.google.com/oauthplayground")
        print("2. Click top-right gear [Settings] -> Check 'Use your own OAuth credentials'")
        print(f"   Client ID: {Config.YOUTUBE_CLIENT_ID}")
        sec_masked = f"{Config.YOUTUBE_CLIENT_SECRET[:4]}...[REDACTED]" if Config.YOUTUBE_CLIENT_SECRET else "[NOT SET]"
        print(f"   Client Secret: {sec_masked}")
        print("3. Select 'YouTube Data API v3 -> https://www.googleapis.com/auth/youtube.upload'")
        print("4. Click Authorize APIs -> Exchange authorization code for tokens")
        print("=" * 60)
        return

    if creds and creds.refresh_token:
        print("\n[OK] Authorization successful!", flush=True)
        tok_masked = f"{creds.refresh_token[:6]}...[REDACTED]"
        print(f"   Fresh Refresh Token: {tok_masked}", flush=True)

        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            updated = False
            for line in lines:
                if line.startswith("YOUTUBE_REFRESH_TOKEN="):
                    new_lines.append(f'YOUTUBE_REFRESH_TOKEN="{creds.refresh_token}"\n')
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                new_lines.append(f'\nYOUTUBE_REFRESH_TOKEN="{creds.refresh_token}"\n')

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            print("[SUCCESS] YOUTUBE_REFRESH_TOKEN has been automatically saved to your .env file!", flush=True)

if __name__ == "__main__":
    main()
