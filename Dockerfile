# Video / Story Downloader — production image for Render / any Docker host
#
# Includes the bgutil PO-token provider so YouTube works WITHOUT cookies on
# datacenter IPs. Instagram cookieless still needs a residential proxy — set the
# YTDLP_PROXY env var on Render to enable it (see COOKIES.md → Cookieless mode).
FROM python:3.12-slim

# System deps:
#   ffmpeg            -> merge HD video+audio
#   git/curl/node     -> build & run the PO-token provider (pure-JS, no browser)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg git curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g yarn && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- YouTube PO-token provider (bgutil) ---------------------------------------
# Build the token-provider server once at image build time. yt-dlp's companion
# plugin (installed via pip below) auto-connects to it on 127.0.0.1:4416 and
# supplies the "proof of origin" token YouTube demands from cloud IPs.
RUN git clone --depth 1 \
      https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && \
    yarn install --frozen-lockfile && \
    npx tsc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides $PORT; default to 5000 locally
ENV PORT=5000
EXPOSE 5000

# Start the PO-token provider in the background, then the web app.
# --timeout 600 so long downloads/merges don't get killed by gunicorn.
CMD node /opt/bgutil/server/build/main.js >/tmp/pot.log 2>&1 & \
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600
