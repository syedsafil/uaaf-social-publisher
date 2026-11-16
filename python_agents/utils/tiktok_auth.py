"""
UAAF Universal 1-Click TikTok OAuth Generator
=============================================
This script launches a local server, opens TikTok OAuth login in your browser,
captures the authorization code, exchanges it for a permanent access token,
and automatically updates your .env file.
"""
import os
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log

PORT = 8085
REDIRECT_URI = f"http://localhost:{PORT}/callback"

class TikTokAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            query = urllib.parse.parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            error = query.get("error", [None])[0]

            if code:
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <html>
                <head><title>UAAF - TikTok Authorized</title></head>
                <body style="font-family:sans-serif; background:#09090b; color:#f4f4f5; text-align:center; padding:50px;">
                    <h1 style="color:#10b981;">🎉 TikTok Authorization Successful!</h1>
                    <p>Your access token has been captured. You can close this browser tab and return to the terminal.</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
                self.server.auth_code = code
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h1>Authorization Failed: {error}</h1>".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def update_env_file(key: str, value: str):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f'{key}="{value}"\n')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}="{value}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    log.info(f"  💾 Updated .env: {key}=***")


def main():
    client_key = Config.TIKTOK_CLIENT_KEY
    client_secret = Config.TIKTOK_CLIENT_SECRET

    if not client_key or not client_secret:
        log.error("❌ TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET missing in .env")
        return

    csrf_state = "uaaf_state_2026"
    scopes = "user.info.basic,video.upload,video.publish"

    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={client_key}"
        f"&scope={scopes}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state={csrf_state}"
    )

    log.info("=" * 60)
    log.info("  🎵 UAAF TIKTOK 1-CLICK AUTH GENERATOR")
    log.info("=" * 60)
    log.info(f"  🌐 Redirect URI: {REDIRECT_URI}")
    log.info(f"  👉 Opening authorization in browser...")
    log.info(f"  🔗 URL: {auth_url}")

    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), TikTokAuthHandler)
    server.auth_code = None

    try:
        while not server.auth_code:
            server.handle_request()
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        return

    code = server.auth_code
    log.info(f"  🔑 Captured Auth Code: {code[:10]}...")

    # Exchange code for access token
    log.info("  🔄 Exchanging code for Access Token from TikTok API...")
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    try:
        r = httpx.post(token_url, data=payload, timeout=30)
        data = r.json()
        if "access_token" in data:
            access_token = data["access_token"]
            refresh_token = data.get("refresh_token", "")
            open_id = data.get("open_id", "")

            update_env_file("TIKTOK_ACCESS_TOKEN", access_token)
            if refresh_token:
                update_env_file("TIKTOK_REFRESH_TOKEN", refresh_token)

            log.info("=" * 60)
            log.info("  🎉 SUCCESS! TikTok Access Token saved to .env!")
            log.info("=" * 60)
        else:
            log.error(f"❌ TikTok Token exchange error: {data}")
    except Exception as e:
        log.error(f"❌ Token request failed: {e}")

if __name__ == "__main__":
    main()
