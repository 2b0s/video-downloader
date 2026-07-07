"""
Social Media Video / Story Downloader
-------------------------------------
Local web app that wraps yt-dlp. Paste a URL, pick a quality, download.
Supports YouTube, TikTok, Instagram, Facebook, Twitter/X, and 1000+ sites.

Run:  python app.py   ->  open http://127.0.0.1:5000
"""

import os
import re
import glob
import shutil
import tempfile
import threading
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Where finished files land before being sent to the browser.
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Optional: a cookies.txt next to this file lets you fetch private / login-gated
# stories (Instagram/Facebook). Export it with a browser "Get cookies.txt" extension.
COOKIES_FILE = Path(__file__).parent / "cookies.txt"


def find_ffmpeg():
    """Locate ffmpeg so yt-dlp can merge HD video+audio streams."""
    exe = shutil.which("ffmpeg")
    if exe:
        return str(Path(exe).parent)
    # winget installs under this path; PATH may not be refreshed in this session.
    for base in [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    ]:
        if base.exists():
            hits = list(base.glob("**/ffmpeg.exe"))
            if hits:
                return str(hits[0].parent)
    return None


FFMPEG_DIR = find_ffmpeg()


def base_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "nocheckcertificate": True,
    }
    if FFMPEG_DIR:
        opts["ffmpeg_location"] = FFMPEG_DIR
    if COOKIES_FILE.exists():
        opts["cookiefile"] = str(COOKIES_FILE)
    return opts


def safe_name(text):
    text = re.sub(r'[\\/:*?"<>|]+', "_", text or "video")
    return text.strip()[:120] or "video"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def info():
    """Fetch metadata + available qualities without downloading."""
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Please paste a URL."}), 400

    try:
        with YoutubeDL({**base_opts(), "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Could not read this link: {e}"}), 400

    # Playlists / story collections: use the first entry for preview.
    if data.get("_type") == "playlist" and data.get("entries"):
        entries = [e for e in data["entries"] if e]
        data = entries[0] if entries else data

    # Collect the distinct video heights that are actually available.
    heights = set()
    for f in data.get("formats", []):
        if f.get("vcodec") not in (None, "none") and f.get("height"):
            heights.add(int(f["height"]))

    qualities = []
    for h in sorted(heights, reverse=True):
        qualities.append({"id": f"h{h}", "label": f"{h}p", "height": h})
    if not qualities:  # some sites expose one merged file only
        qualities.append({"id": "best", "label": "Best available", "height": 0})
    qualities.append({"id": "audio", "label": "Audio only (MP3)", "height": -1})

    return jsonify({
        "title": data.get("title") or "Untitled",
        "uploader": data.get("uploader") or data.get("channel") or "",
        "thumbnail": data.get("thumbnail"),
        "duration": data.get("duration"),
        "qualities": qualities,
    })


@app.route("/api/download", methods=["POST"])
def download():
    body = request.json or {}
    url = body.get("url", "").strip()
    quality = body.get("quality", "best")
    if not url:
        return jsonify({"error": "Missing URL."}), 400

    tmpdir = tempfile.mkdtemp(dir=DOWNLOAD_DIR)
    outtmpl = str(Path(tmpdir) / "%(title).100s.%(ext)s")
    opts = {**base_opts(), "outtmpl": outtmpl, "restrictfilenames": False}

    if quality == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif quality.startswith("h"):
        h = quality[1:]
        # Prefer mp4 for compatibility; fall back to best under that height.
        opts["format"] = (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        )
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    try:
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": f"Download failed: {e}"}), 400

    files = [f for f in glob.glob(str(Path(tmpdir) / "*")) if os.path.isfile(f)]
    if not files:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Nothing was downloaded."}), 400

    filepath = max(files, key=os.path.getsize)  # the merged/final file
    filename = safe_name(Path(filepath).stem) + Path(filepath).suffix

    @after_this_request
    def cleanup(response):
        # Remove the temp copy shortly after the response is streamed.
        def _rm():
            shutil.rmtree(tmpdir, ignore_errors=True)
        threading.Timer(30, _rm).start()
        return response

    return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    print("=" * 55)
    print("  Video / Story Downloader")
    print("  ffmpeg:", FFMPEG_DIR or "NOT FOUND (HD merge may fail)")
    print("  cookies:", "loaded" if COOKIES_FILE.exists() else "none")
    port = int(os.environ.get("PORT", 5000))
    print(f"  Open:   http://127.0.0.1:{port}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False)
