"""
UAAF EMAIL APPROVAL CONTROLLER — Resend API
═══════════════════════════════════════════════════════════════
Jab video render complete ho jaye, ye script chalta hai:
1. Chairman ko email bhejta hai (Resend API — FREE 100/day)
2. Email mein dark-mode luxury HTML template + video preview thumbnail
3. Do buttons: [Approve & Deploy] + [Reject/Regenerate]
4. Button click → Next.js API → Database update → Multi-platform publish

Resend API: https://resend.com (FREE tier, no credit card)
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import json
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log


async def send_approval_email(
    creative_id: str,
    title: str,
    niche: str,
    hook: str,
    caption: str,
    thumbnail_url: str,
    video_url: str,
    quality_score: int,
    predicted_views: int,
    director: str = "Muse",
) -> Dict:
    """
    Video render complete hone ke baad Chairman ko email bhejo.
    Email mein Approve/Reject buttons hain jo Next.js API ko hit karte hain.

    Args:
        creative_id: Database creative ID
        title: Video title
        niche: Luxury niche (e.g., "Luxury Coffee")
        hook: 6-word hook
        caption: Full caption
        thumbnail_url: Hosted thumbnail image URL
        video_url: Hosted video .mp4 URL
        quality_score: 0-100 quality score
        predicted_views: Predicted view count
        director: AI director name

    Returns:
        { success: bool, message_id: str }
    """
    log.info(f"Email Approver: sending approval email for '{title}'")
    log.info(f"  To: {Config.CHAIRMAN_EMAIL}")
    log.info(f"  Creative ID: {creative_id}")

    # ── Build approval/reject URLs ──
    # Ye links Next.js API ko hit karenge
    base_url = Config.WEBHOOK_BASE_URL or "http://localhost:3000"

    # Secure token (simple hash — production mein JWT use karo)
    import hashlib
    secure_token = hashlib.sha256(
        f"{creative_id}-{Config.NEXTAUTH_SECRET or 'uaaf'}-{datetime.now(timezone.utc).date()}"
        .encode()
    ).hexdigest()[:32]

    approve_url = f"{base_url}/api/approve-email?action=approve&id={creative_id}&token={secure_token}"
    reject_url = f"{base_url}/api/approve-email?action=reject&id={creative_id}&token={secure_token}"

    # ── Build HTML email template (dark-mode luxury) ──
    html = _build_email_template(
        title=title,
        niche=niche,
        hook=hook,
        caption=caption,
        thumbnail_url=thumbnail_url,
        video_url=video_url,
        quality_score=quality_score,
        predicted_views=predicted_views,
        director=director,
        approve_url=approve_url,
        reject_url=reject_url,
    )

    # ── Send via Resend API ──
    resend_key = Config.RESEND_API_KEY
    if not resend_key or resend_key.startswith("re_your"):
        log.warn("Resend API key not configured — skipping email")
        return {"success": False, "error": "RESEND_API_KEY not set in .env"}

    payload = {
        "from": "UAAF Factory <noreply@resend.dev>",
        "to": [Config.CHAIRMAN_EMAIL],
        "subject": f"🎬 Video Ready: {title} — Approve to Deploy",
        "html": html,
        "headers": {
            "X-Entity-Ref-ID": creative_id,
        },
    }

    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()

        message_id = result.get("id", "unknown")
        log.info(f"✅ Email sent successfully! Message ID: {message_id}")
        log.info(f"  Chairman can approve at: {approve_url[:80]}...")

        return {"success": True, "message_id": message_id}

    except httpx.HTTPStatusError as e:
        log.error(f"Resend API error: {e.response.status_code} — {e.response.text}")
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        log.error(f"Email send failed: {e}")
        return {"success": False, "error": str(e)}

async def send_published_success_email(
    title: str,
    results: Dict[str, Dict],
) -> Dict:
    """Send a live confirmation email with links to all published platforms."""
    resend_key = Config.RESEND_API_KEY
    if not resend_key or resend_key.startswith("re_your"):
        log.warn("Resend API key not configured — skipping email")
        return {"success": False, "error": "RESEND_API_KEY not set"}

    log.info(f"Email Approver: sending publication confirmation email for '{title}'")

    # Build platform links list
    links_html = ""
    for platform, res in results.items():
        status = res.get("status")
        url = res.get("url")
        icon = "✅" if status == "success" else "❌"
        color = "#D4AF37" if status == "success" else "#e86439"
        
        if url and url.startswith("http"):
            link_item = f'<a href="{url}" style="color:{color};font-weight:600;text-decoration:underline;">{platform.upper()} Post Link</a>'
        else:
            link_item = f'<span style="color:#888;">{res.get("error", "Not published")}</span>'
            
        links_html += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
          <td style="padding:12px 0;font-size:14px;color:#fff;">{icon} <strong>{platform.capitalize()}</strong></td>
          <td style="padding:12px 0;font-size:14px;text-align:right;">{link_item}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#07090e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#fff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#0e121a;border-radius:24px;border:1px solid rgba(212,175,55,0.3);overflow:hidden;">
          <tr>
            <td style="padding:32px 40px;background:linear-gradient(135deg,rgba(212,175,55,0.15),transparent);border-bottom:1px solid rgba(255,255,255,0.06);">
              <div style="font-size:12px;color:#D4AF37;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;">⚡ UAAF Live Dispatch</div>
              <h1 style="margin:8px 0 0 0;font-size:24px;color:#fff;">🚀 Video Live Published Across All Platforms!</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px;">
              <p style="font-size:15px;color:#bbb;line-height:1.6;margin-top:0;">
                Chairman, aapki video <strong>"{title}"</strong> live publish ho chuki hai!
              </p>
              
              <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
                {links_html}
              </table>

              <div style="background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.25);border-radius:12px;padding:16px;margin-top:20px;">
                <p style="margin:0;font-size:13px;color:#D4AF37;line-height:1.5;">
                  💬 <strong>Test Your AI Comment Engine:</strong> Ab aap kisi doosre account se in posts par <strong>"KIT"</strong> ya <strong>"GET"</strong> comment karke live AI auto-reply aur DM funnel check kar sakte hain!
                </p>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 40px;background:rgba(0,0,0,0.4);border-top:1px solid rgba(255,255,255,0.04);font-size:11px;color:#666;text-align:center;">
              UAAF Universal AI Ad Factory · Autonomous Multi-Platform Operating System
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    payload = {
        "from": "UAAF Factory <noreply@resend.dev>",
        "to": [Config.CHAIRMAN_EMAIL],
        "subject": f"🚀 Live Published: {title} Across All Platforms!",
        "html": html,
    }

    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.resend.com/emails", headers=headers, json=payload)
            resp.raise_for_status()
            res_json = resp.json()
            log.info(f"✅ Published confirmation email sent! ID: {res_json.get('id')}")
            return {"success": True, "message_id": res_json.get("id")}
    except Exception as e:
        log.warn(f"Published confirmation email failed: {e}")
        return {"success": False, "error": str(e)}


def _build_email_template(
    title: str,
    niche: str,
    hook: str,
    caption: str,
    thumbnail_url: str,
    video_url: str,
    quality_score: int,
    predicted_views: int,
    director: str,
    approve_url: str,
    reject_url: str,
) -> str:
    """
    Dark-mode luxury HTML email template.
    Champagne + charcoal palette. Minimal, Apple-style.
    """
    quality_color = "#D4AF37" if quality_score >= 90 else "#e5a823" if quality_score >= 75 else "#e86439"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UAAF — Video Ready for Approval</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0b;min-height:100vh;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <!-- Container -->
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#121214;border-radius:16px;overflow:hidden;border:1px solid rgba(212,175,55,0.15);">

          <!-- Header -->
          <tr>
            <td style="padding:32px 40px 24px;border-bottom:1px solid rgba(255,255,255,0.06);">
              <table width="100%">
                <tr>
                  <td>
                    <div style="font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#D4AF37;font-weight:600;">UAAF · Universal AI Ad Factory</div>
                    <div style="font-size:13px;color:#6b6b70;margin-top:4px;">Chairman's Daily Approval</div>
                  </td>
                  <td align="right">
                    <div style="font-size:11px;color:#4a4a50;text-align:right;">
                      {datetime.now(timezone.utc).strftime("%b %d, %Y")}<br>
                      <span style="color:#D4AF37;">●</span> Render Complete
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Video Preview -->
          <tr>
            <td style="padding:0;">
              <a href="{video_url}" style="display:block;text-decoration:none;">
                <div style="position:relative;width:100%;height:340px;overflow:hidden;background:#000;">
                  <img src="{thumbnail_url}" alt="{title}" style="width:100%;height:100%;object-fit:cover;opacity:0.9;">
                  <!-- Gradient overlay -->
                  <div style="position:absolute;bottom:0;left:0;right:0;height:60%;background:linear-gradient(to top,rgba(10,10,11,0.95) 0%,transparent 100%);"></div>
                  <!-- Play button -->
                  <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:64px;height:64px;background:rgba(255,255,255,0.9);border-radius:50%;display:flex;align-items:center;justify-content:center;">
                    <div style="width:0;height:0;border-top:12px solid transparent;border-bottom:12px solid transparent;border-left:20px solid #D4AF37;margin-left:4px;"></div>
                  </div>
                  <!-- Title overlay -->
                  <div style="position:absolute;bottom:24px;left:40px;right:40px;">
                    <div style="font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:#D4AF37;margin-bottom:8px;font-weight:600;">{niche}</div>
                    <div style="font-size:24px;color:#ffffff;font-weight:600;letter-spacing:-0.02em;line-height:1.2;">{title}</div>
                  </div>
                </div>
              </a>
            </td>
          </tr>

          <!-- Details -->
          <tr>
            <td style="padding:32px 40px;">
              <!-- Hook -->
              <div style="margin-bottom:24px;">
                <div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:#6b6b70;margin-bottom:8px;">The Hook</div>
                <div style="font-size:18px;color:#e8e8ea;font-style:italic;font-family:Georgia,serif;">&ldquo;{hook}&rdquo;</div>
              </div>

              <!-- Caption -->
              <div style="margin-bottom:24px;">
                <div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:#6b6b70;margin-bottom:8px;">Caption</div>
                <div style="font-size:14px;color:#a8a8ac;line-height:1.6;">{caption}</div>
              </div>

              <!-- Stats -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
                <tr>
                  <td style="background:rgba(255,255,255,0.03);border-radius:12px;padding:16px;text-align:center;border:1px solid rgba(255,255,255,0.04);">
                    <div style="font-size:28px;font-weight:700;color:{quality_color};font-variant-numeric:tabular-nums;">{quality_score}</div>
                    <div style="font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#6b6b70;margin-top:4px;">Quality Score</div>
                  </td>
                  <td style="width:12px;"></td>
                  <td style="background:rgba(255,255,255,0.03);border-radius:12px;padding:16px;text-align:center;border:1px solid rgba(255,255,255,0.04);">
                    <div style="font-size:28px;font-weight:700;color:#D4AF37;font-variant-numeric:tabular-nums;">{predicted_views // 1000}K</div>
                    <div style="font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#6b6b70;margin-top:4px;">Pred. Views</div>
                  </td>
                  <td style="width:12px;"></td>
                  <td style="background:rgba(255,255,255,0.03);border-radius:12px;padding:16px;text-align:center;border:1px solid rgba(255,255,255,0.04);">
                    <div style="font-size:28px;font-weight:700;color:#e8e8ea;font-variant-numeric:tabular-nums;">{director}</div>
                    <div style="font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#6b6b70;margin-top:4px;">AI Director</div>
                  </td>
                </tr>
              </table>

              <!-- Action Buttons -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:0 0 12px 0;">
                    <a href="{approve_url}" style="display:block;background:#D4AF37;color:#0a0a0b;font-size:16px;font-weight:700;text-decoration:none;text-align:center;padding:18px;border-radius:12px;letter-spacing:0.02em;">
                      ✓ Approve &amp; Deploy to All Platforms
                    </a>
                  </td>
                </tr>
                <tr>
                  <td>
                    <a href="{reject_url}" style="display:block;background:rgba(255,255,255,0.05);color:#e86439;font-size:14px;font-weight:600;text-decoration:none;text-align:center;padding:14px;border-radius:12px;border:1px solid rgba(232,100,57,0.3);">
                      ✗ Reject / Regenerate
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Note -->
              <div style="margin-top:24px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.06);">
                <div style="font-size:12px;color:#4a4a50;line-height:1.6;">
                  <strong style="color:#6b6b70;">⚡ Quick Decision:</strong> Approve karne pe video instant Instagram, TikTok, YouTube, X pe publish hogi.<br>
                  <strong style="color:#6b6b70;">🔄 Regenerate:</strong> Reject karne pe AI naya concept generate karega.<br>
                  <strong style="color:#6b6b70;">📱 Dashboard:</strong> <a href="{Config.WEBHOOK_BASE_URL or 'http://localhost:3000'}" style="color:#D4AF37;text-decoration:none;">Chairman Dashboard</a> pe bhi review kar sakte hain.
                </div>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px;background:rgba(0,0,0,0.3);border-top:1px solid rgba(255,255,255,0.04);">
              <div style="font-size:10px;color:#3a3a40;text-align:center;line-height:1.8;">
                UAAF · Universal AI Ad Factory<br>
                Autonomous Creative Operating System · v1.0<br>
                This email was sent automatically by the UAAF pipeline.
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


if __name__ == "__main__":
    # Test: send a sample email
    import asyncio

    result = asyncio.run(send_approval_email(
        creative_id="test_001",
        title="Cedar & Smoke — The Pour",
        niche="Luxury Coffee",
        hook="Most coffee is noise. This one is silence.",
        caption="Single-origin Ethiopian beans, hand-roasted in cedar smoke for 72 hours.",
        thumbnail_url="https://image.pollinations.ai/prompt/luxury%20coffee%20pour%20macro?width=1080&height=1920",
        video_url="https://example.com/video.mp4",
        quality_score=96,
        predicted_views=482000,
    ))
    print(json.dumps(result, indent=2))
