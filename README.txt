# Telegram Forwarder Starter (Wispbyte)

This is a small starter backend, not the full web dashboard yet. It supports URL filtering, live forwarding, optional recent-history forwarding, media forwarding, and an ignore-bot toggle per job.

## Important limitations
- This starter uses one Telegram user session for all configured jobs. Multiple independent sessions and the web dashboard are not implemented yet.
- It forwards messages only from chats your account can access.
- It uses Telegram's native forwarding, so the original source may remain visible. Media/captions are forwarded when Telegram permits.
- Keep `sessions/primary.session` private. Anyone with it may be able to access your Telegram account.
- Telegram API credentials and session files must never be posted publicly.
- Wispbyte free resources are limited; test with one job first.

## Files
- `main.py`: application
- `requirements.txt`: Python dependency
- `config.example.json`: example jobs

## Configure on Wispbyte
1. Upload `main.py`, `requirements.txt`, and `config.example.json` to the server's Files section.
2. Create a copy of `config.example.json` named `config.json` using the file manager's editor.
3. In Startup, set Python packages to `Telethon>=1.36,<2` if the panel has a package field.
4. Set startup command to `python main.py` (or `python3 main.py` if required by the image).
5. Add environment variables `TG_API_ID` and `TG_API_HASH` in Startup. Get them from https://my.telegram.org. Never put them in public files.
6. Authentication: the first run needs a Telegram login code and may need your 2FA password. If Wispbyte console cannot accept interactive input, do not try to paste codes into public logs. We will instead create a session locally and transfer the session file privately, or use another supported secure login workflow.
7. Start and check Logs.

## Configure each job
In `config.json`, replace source and destination placeholders with chat usernames or numeric IDs. Set `enabled` true for jobs you want active.
- Flezen: `match_domains`: `["flezen.com"]`
- Diskwala: `match_domains`: `["diskwala.com"]`
- Vidbunker: `match_domains`: `["vidbunker.in/watch/"]`
- `ignore_bot_messages`: true/false
- `history_limit`: 0 means no history scan; e.g. 100 means inspect the 100 most recent source messages at startup.
- `include_media`: true forwards messages with attachments if the text/caption matches the domain.
- `ignore_text`: optional list of text fragments to skip.

The source chat must contain a matching URL in the message text or caption for it to forward.
