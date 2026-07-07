# Video / Story Downloader — production image for Render / any Docker host
FROM python:3.12-slim

# ffmpeg is required to merge HD video+audio streams
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides $PORT; default to 5000 locally
ENV PORT=5000
EXPOSE 5000

# --timeout 600 so long downloads/merges don't get killed by gunicorn
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600
