# Making YouTube & Instagram work (cookies)

YouTube and Instagram block anonymous downloads with *"Sign in to confirm you're
not a bot"* / *"rate-limit for accessing posts anonymously."* The fix is to give
yt-dlp your **logged-in session** as a `cookies.txt` file. This app loads a file
named `cookies.txt` (placed next to `app.py`) automatically.

## How to create cookies.txt (5 min)

1. In **Chrome**, install the extension **"Get cookies.txt LOCALLY"**
   (Chrome Web Store — it exports in the Netscape format yt-dlp needs).
2. Open **https://www.youtube.com** and make sure you are **logged in**.
   - Best practice: open an **Incognito** window, log in to YouTube there, export,
     then close it *without* logging out — this gives a stable cookie set.
3. Click the extension icon → **Export** (or "Export As → cookies.txt").
   A file `cookies.txt` (or `youtube.com_cookies.txt`) downloads.
4. Move that file into:  `C:\Users\Abbas Al-Ashwal\video-downloader\`
   and rename it to exactly **`cookies.txt`**.
5. Restart the app (`run.bat`). It will print `cookies: loaded`.

### Also want Instagram?
Repeat step 2–3 on **https://www.instagram.com** while logged in, then **append**
those lines to the same `cookies.txt` (open both in Notepad, paste Instagram's
cookie lines under YouTube's — keep the first `# Netscape...` header only once).

## Cookieless mode (the hosted Render site)

The Docker image now bakes in the **bgutil PO-token provider**, so **YouTube works
without cookies** even on Render's datacenter IP — nothing to configure, it just
runs. (yt-dlp fetches the "proof of origin" token from a local helper process.)

**Instagram** is stricter: it blocks anonymous datacenter access, so cookieless IG
only works through a **residential proxy**. To turn it on:

1. Get a residential/rotating proxy (e.g. Webshare, IPRoyal — a few $/mo).
2. In the Render dashboard → your service → **Environment**, add:
   `YTDLP_PROXY = http://user:pass@host:port`   (or `socks5://…`)
3. Save — Render redeploys. Now both YouTube **and** Instagram route through a
   home-style IP and download without cookies.

Leaving `YTDLP_PROXY` unset keeps YouTube cookieless (via the PO-token provider);
Instagram then still needs a cookies.txt or the proxy above.

## Important limits
- **Cookies expire.** If it stops working after days/weeks, re-export.
- **Never commit cookies.txt to GitHub** — it's your login. `.gitignore` already
  excludes it.
- **On Render (cloud):** YouTube blocks datacenter IPs *even with cookies* — it may
  still fail there. Instagram/TikTok usually work on Render with cookies. YouTube is
  most reliable from the **local** app (your home IP + your cookies).
