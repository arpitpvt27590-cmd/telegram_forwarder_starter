import asyncio
import json
import logging
import os
import re
from pathlib import Path
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SESSIONS_DIR = ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("forwarder")


def load_config():
    if not CONFIG_PATH.exists():
        raise SystemExit("Missing config.json. Copy config.example.json to config.json and edit it.")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not cfg.get("jobs"):
        raise SystemExit("config.json must contain at least one job in 'jobs'.")
    return cfg


def matches_job(message, job):
    text = message.message or ""
    domains = [d.lower().strip() for d in job.get("match_domains", []) if d.strip()]
    if not domains:
        return False
    lower = text.lower()
    return any(domain in lower for domain in domains)


def should_ignore(message, job, sender_is_bot):
    if job.get("ignore_bot_messages", True) and sender_is_bot:
        return True
    text = message.message or ""
    ignored = [x.lower() for x in job.get("ignore_text", []) if x]
    if any(x in text.lower() for x in ignored):
        return True
    allowed_types = job.get("include_media", True)
    if not allowed_types and message.media:
        return True
    return False


async def main():
    cfg = load_config()
    api_id = int(os.environ.get("TG_API_ID", "0") or 0)
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    if not api_id or not api_hash:
        raise SystemExit("Set TG_API_ID and TG_API_HASH in Wispbyte Startup environment variables.")

    # A single authenticated Telegram account can run multiple jobs.
    # Add more account configs in later versions if needed; never share session files.
    session_name = cfg.get("session_name", "primary")
    session_path = str(SESSIONS_DIR / session_name)
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    log("Connected Telegram account id=%s username=%s", me.id, getattr(me, "username", None))

    jobs = cfg["jobs"]
    for idx, job in enumerate(jobs, 1):
        if not job.get("enabled", True):
            continue
        source = job.get("source")
        destination = job.get("destination")
        if source is None or destination is None:
            log("Job %s skipped: source and destination are required", job.get("name", idx))
            continue
        log("Enabled job '%s': %s -> %s", job.get("name", f"job-{idx}"), source, destination)

        @client.on(events.NewMessage(chats=source))
        async def live_handler(event, job=job):
            try:
                msg = event.message
                sender = await event.get_sender()
                is_bot = bool(getattr(sender, "bot", False))
                if should_ignore(msg, job, is_bot) or not matches_job(msg, job):
                    return
                await client.forward_messages(job["destination"], msg)
                log("[%s] forwarded live message %s", job.get("name", "job"), msg.id)
            except FloodWaitError as e:
                log("Telegram rate limit: wait %s seconds", e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception:
                log("[%s] live forward failed", job.get("name", "job"), exc_info=True)

    # Optional past-history forwarding. Runs once at startup for jobs configured with history_limit > 0.
    for idx, job in enumerate(jobs, 1):
        if not job.get("enabled", True):
            continue
        limit = int(job.get("history_limit", 0) or 0)
        if limit <= 0:
            continue
        source, destination = job.get("source"), job.get("destination")
        log("[%s] scanning up to %s recent messages", job.get("name", f"job-{idx}"), limit)
        try:
            messages = []
            async for msg in client.iter_messages(source, limit=limit, reverse=True):
                messages.append(msg)
            for msg in messages:
                try:
                    sender = await msg.get_sender()
                    if should_ignore(msg, job, bool(getattr(sender, "bot", False))) or not matches_job(msg, job):
                        continue
                    await client.forward_messages(destination, msg)
                    log("[%s] forwarded history message %s", job.get("name", "job"), msg.id)
                    await asyncio.sleep(float(job.get("history_delay_seconds", 1.0)))
                except FloodWaitError as e:
                    log("Telegram rate limit: wait %s seconds", e.seconds)
                    await asyncio.sleep(e.seconds)
                except Exception:
                    log("[%s] history message failed", job.get("name", "job"), exc_info=True)
        except Exception:
            log("[%s] history scan failed", job.get("name", "job"), exc_info=True)

    log("Forwarder is running. Keep this process online for live forwarding.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
