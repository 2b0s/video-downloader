# Deploying to Render (free public website)

Your app is already a git repo with a Dockerfile. Two steps: push to GitHub, then deploy on Render.

## 1. Put the code on GitHub

**Easiest (GitHub CLI):** in PowerShell, inside this folder:
```powershell
cd "$env:USERPROFILE\video-downloader"
gh auth login          # choose: GitHub.com > HTTPS > login with browser
gh repo create video-downloader --public --source . --push
```
That creates the repo and pushes in one go.

**Manual alternative:** create an empty repo at https://github.com/new (name it
`video-downloader`, don't add a README), then:
```powershell
cd "$env:USERPROFILE\video-downloader"
git remote add origin https://github.com/<YOUR-USERNAME>/video-downloader.git
git branch -M main
git push -u origin main
```

## 2. Deploy on Render

1. Go to https://render.com and sign up (free — "Sign in with GitHub" is easiest).
2. Click **New +  →  Web Service**.
3. Connect your GitHub and pick the **video-downloader** repo.
4. Render auto-detects the **Dockerfile**. Leave defaults:
   - Runtime: **Docker**
   - Plan: **Free**
   - (render.yaml already sets health check + auto-deploy)
5. Click **Create Web Service**. First build takes ~3–5 min.
6. You'll get a public URL like `https://video-downloader-xxxx.onrender.com`.

Every `git push` afterward auto-redeploys.

## Notes
- **Free tier sleeps** after ~15 min idle; the first visit then takes ~30s to wake.
- **YouTube / Instagram** may show *"Sign in to confirm you're not a bot"* on cloud
  IPs. To fix, add a `cookies.txt` (see COOKIES.md) — but don't commit it publicly.
- TikTok, Twitter/X, Facebook public videos generally work without cookies.
