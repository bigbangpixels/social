"""Big Bang Pixels TikTok publisher (GitHub Actions, every hour): sends the carousels of _social/tiktok.json that are
due to the BBP TikTok inbox as drafts (Content Posting API, MEDIA_UPLOAD, photos pulled from this site). The user then
adds a sound (and the AI label when the entry says so) in the TikTok app and posts.

Queue entries (written by the PC, Pinterest Scheduler/social_queue.py):
  {"id": "...", "when": "2026-11-24T00:12:00+00:00", "title": "...", "description": "...", "ai": false,
   "images": ["tiktok/<id>/01-ab12cd34.jpg", ...], "status": "queued"}
The runner sets status "sent" (publish_id, sent_at) or "error" (error, tries); an entry more than 36 hours late is
"missed" (the next one keeps the daily rhythm). One draft per run at most.

Secrets: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN. `--check` only tests the connection.
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "_social" / "tiktok.json"
SITE_URL = "https://social.bigbangpixels.store/"
TT_API = "https://open.tiktokapis.com/v2"
LATE = dt.timedelta(hours=36)


def secret(name):
    v = (os.environ.get(name) or "").strip()
    if not v:
        sys.exit(f"secret {name} is missing")
    return v


def token():
    r = requests.post(f"{TT_API}/oauth/token/", timeout=30, data={
        "client_key": secret("TIKTOK_CLIENT_KEY"), "client_secret": secret("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": secret("TIKTOK_REFRESH_TOKEN")})
    j = r.json()
    if "access_token" not in j:
        sys.exit(f"TikTok token refresh failed: {j.get('error_description') or j.get('error')}")
    if j.get("refresh_token") and j["refresh_token"] != secret("TIKTOK_REFRESH_TOKEN"):
        print("NOTE: TikTok issued a new refresh token; run `python tiktok_bbp.py secrets` on the PC to update it")
    return j["access_token"]


def call(tok, path, body):
    r = requests.post(f"{TT_API}{path}", json=body, timeout=60,
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"})
    j = r.json()
    if r.status_code >= 400 or j.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"{path} -> {r.status_code}: {str(j.get('error', j))[:300]}")
    return j.get("data", {})


def send(tok, e):
    urls = [SITE_URL + p for p in e["images"]]
    for u in urls:
        requests.head(u, timeout=30).raise_for_status()
    pid = call(tok, "/post/publish/content/init/", {
        "post_info": {"title": e["title"][:90], "description": e["description"][:4000]},
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls},
        "post_mode": "MEDIA_UPLOAD", "media_type": "PHOTO"})["publish_id"]
    status = ""
    for _ in range(20):
        status = call(tok, "/post/publish/status/fetch/", {"publish_id": pid}).get("status", "")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            break
        time.sleep(6)
    if status == "FAILED":
        raise RuntimeError(f"TikTok could not take the carousel (publish_id {pid})")
    return pid, status


def main():
    if "--check" in sys.argv:
        tok = token()
        r = requests.get(f"{TT_API}/user/info/?fields=display_name", timeout=30,
                         headers={"Authorization": f"Bearer {tok}"})
        print("connected:", r.json().get("data", {}).get("user", {}).get("display_name"))
        return
    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else []
    now = dt.datetime.now(dt.timezone.utc)
    changed, sent = False, False
    for e in sorted(queue, key=lambda x: x["when"]):
        if e.get("status") not in ("queued", "error"):
            continue
        when = dt.datetime.fromisoformat(e["when"])
        if when > now:
            break
        if now - when > LATE:
            e["status"], changed = "missed", True
            print(f"missed: {e['id']} (due {e['when']})")
            continue
        if sent or e.get("tries", 0) >= 3:
            continue
        try:
            pid, status = send(token(), e)
            e.update(status="sent", publish_id=pid, tiktok_status=status, sent_at=now.isoformat(timespec="seconds"))
            print(f"sent: {e['id']} -> {status}")
            sent = True
        except (RuntimeError, requests.RequestException) as err:
            e.update(status="error", error=str(err)[:300], tries=e.get("tries", 0) + 1)
            print(f"error: {e['id']}: {err}")
        changed = True
    if changed:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
