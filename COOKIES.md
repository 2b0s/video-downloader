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

## Important limits
- **Cookies expire.** If it stops working after days/weeks, re-export.
- **Never commit cookies.txt to GitHub** — it's your login. `.gitignore` already
  excludes it.
- **On Render (cloud):** YouTube blocks datacenter IPs *even with cookies* — it may
  still fail there. Instagram/TikTok usually work on Render with cookies. YouTube is
  most reliable from the **local** app (your home IP + your cookies).
