# Video / Story Downloader — production image for Render / any Docker host
#
# Cookieless YouTube: we base the image on the official bgutil PO-token provider
# image (Node 25 + prebuilt server + working `canvas` native dep) and layer the
# Python web app on top. yt-dlp's companion plugin auto-connects to the provider
# on 127.0.0.1:4416 and supplies the "proof of origin" token YouTube demands from
# datacenter IPs. Instagram cookieless still needs a residential proxy — set the
# YTDLP_PROXY env var on Render (see COOKIES.md → Cookieless mode).
#
# Pin the provider version to the pip plugin version in requirements.txt.
FROM brainicism/bgutil-ytdlp-pot-provider:1.3.1

# apt + running the provider need root (the base image runs as USER node).
USER root

# ffmpeg -> merge HD video+audio;  python3 -> run the Flask app.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Debian marks the system Python as externally-managed, so use a venv.
ENV VENV=/opt/venv
RUN python3 -m venv "$VENV"
ENV PATH="$VENV/bin:$PATH"

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides $PORT; default to 5000 locally
ENV PORT=5000
EXPOSE 5000

# The base image sets ENTRYPOINT to the provider; reset it so our CMD runs as-is.
ENTRYPOINT []

# Start the PO-token provider (built into the base image at /app) in the
# background on :4416, then the web app. --timeout 600 so long downloads/merges
# aren't killed by gunicorn.
CMD node /app/build/main.js >/tmp/pot.log 2>&1 & \
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600
