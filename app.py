"""
Social Media Video / Story Downloader
-------------------------------------
Local / hosted web app that wraps yt-dlp. Paste a URL, pick a quality, download.
Supports YouTube, TikTok, Instagram, Facebook, Twitter/X, and 1000+ sites.

Playlists, story sets and carousels are expanded into a list so each video can
be downloaded separately.

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

# Safety cap so an enormous playlist can't hang the info request forever.
MAX_ENTRIES = 100

# Optional residential proxy (Render env var). Set this to route yt-dlp through a
# home-style IP so YouTube/Instagram don't reject the request as a datacenter bot.
# e.g. YTDLP_PROXY=http://user:pass@host:port  (or socks5://…)
YTDLP_PROXY = os.environ.get("YTDLP_PROXY", "").strip()


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
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
    # Force YouTube's POT-backed web clients so the bgutil token provider is
    # actually used — this is what clears the "confirm you're not a bot" wall on
    # datacenter IPs. Only affects the youtube extractor; other sites are untouched.
    opts["extractor_args"] = {"youtube": {"player_client": ["web_safari", "web", "tv"]}}
    return opts


def safe_name(text):
    text = re.sub(r'[\\/:*?"<>|]+', "_", text or "video")
    return text.strip()[:120] or "video"


def friendly_error(exc):
    """Turn a noisy yt-dlp exception into a short, clear bilingual message."""
    msg = str(exc)
    low = msg.lower()

    if "not a bot" in low or "sign in to confirm" in low:
        return ("تعذّر تحميل هذا الفيديو من يوتيوب: الموقع محظور من عنوان الخادم "
                "(IP مركز بيانات). الحل: أضف proxy سكني في إعدادات Render، "
                "أو استخدم التطبيق المحلي على جهازك. — "
                "YouTube blocked this server's IP; use a residential proxy or the local app.")
    if ("login required" in low or "log in" in low or "rate-limit" in low
            or "rate limit" in low or "requested content is not available" in low):
        return ("هذا المحتوى يتطلب تسجيل دخول أو أنه محدود. جرّب إضافة cookies "
                "أو proxy سكني. — This content needs login / is rate-limited; "
                "add cookies or a residential proxy.")
    if "private" in low:
        return "هذا المحتوى خاص ولا يمكن الوصول إليه. — This content is private."
    if "unavailable" in low or "removed" in low or "deleted" in low:
        return "الفيديو غير متاح أو محذوف. — This video is unavailable or removed."
    if "unsupported url" in low or "no video" in low:
        return "هذا الرابط غير مدعوم أو لا يحتوي على فيديو. — Unsupported link / no video found."

    # Fallback: strip yt-dlp's prefix and the long cookies help text.
    clean = msg.replace("ERROR:", "").split("Use --cookies")[0].strip()
    return f"تعذّر قراءة الرابط: {clean[:250]}"


def best_thumb(entry):
    """Pick a usable thumbnail URL from either the flat field or the list."""
    if entry.get("thumbnail"):
        return entry["thumbnail"]
    thumbs = entry.get("thumbnails") or []
    if thumbs:
        return thumbs[-1].get("url")
    return None


def heights_of(entry):
    """Distinct video heights actually available for one entry."""
    hs = set()
    for f in entry.get("formats", []) or []:
        if f.get("vcodec") not in (None, "none") and f.get("height"):
            hs.add(int(f["height"]))
    return hs


def qualities_from_heights(heights):
    qs = [{"id": f"h{h}", "label": f"{h}p", "height": h}
          for h in sorted(heights, reverse=True)]
    if not qs:  # some sites expose one merged file only
        qs.append({"id": "best", "label": "Best available", "height": 0})
    qs.append({"id": "audio", "label": "Audio only (MP3)", "height": -1})
    return qs


def default_qualities():
    """When per-entry formats aren't known up front (flat playlists)."""
    qs = [{"id": "best", "label": "Best available", "height": 0}]
    qs += [{"id": f"h{h}", "label": f"{h}p", "height": h} for h in (1080, 720, 480, 360)]
    qs.append({"id": "audio", "label": "Audio only (MP3)", "height": -1})
    return qs


def entry_dict(entry, index, parent_url):
    """Normalize one video (single or playlist member) for the frontend."""
    return {
        "index": entry.get("playlist_index") or index,
        # Direct link to the single video; used to download just this one.
        "url": entry.get("webpage_url") or entry.get("original_url") or entry.get("url"),
        "parent_url": parent_url,
        "title": entry.get("title") or f"Video {index}",
        "uploader": entry.get("uploader") or entry.get("channel") or "",
        "thumbnail": best_thumb(entry),
        "duration": entry.get("duration"),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def info():
    """Fetch metadata + available qualities without downloading.

    Always returns a normalized shape:
        { type, title, count, qualities, entries: [ {index,url,title,...}, ... ] }
    A single video is just a one-item list.
    """
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Please paste a URL."}), 400

    try:
        with YoutubeDL({**base_opts(), "skip_download": True,
                        "playlistend": MAX_ENTRIES}) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": friendly_error(e)}), 400

    # ---- Playlist / story set / carousel ----
    if data.get("_type") == "playlist" and data.get("entries"):
        raw = [e for e in data["entries"] if e][:MAX_ENTRIES]
        if not raw:
            return jsonify({"error": "This link has no downloadable videos."}), 400

        entries, all_heights = [], set()
        for i, e in enumerate(raw, start=1):
            all_heights |= heights_of(e)
            entries.append(entry_dict(e, i, parent_url=url))

        qualities = qualities_from_heights(all_heights) if all_heights else default_qualities()
        return jsonify({
            "type": "playlist",
            "title": data.get("title") or "Playlist",
            "count": len(entries),
            "qualities": qualities,
            "entries": entries,
        })

    # ---- Single video ----
    qualities = qualities_from_heights(heights_of(data))
    return jsonify({
        "type": "video",
        "title": data.get("title") or "Untitled",
        "count": 1,
        "qualities": qualities,
        "entries": [entry_dict(data, 1, parent_url=url)],
    })


@app.route("/api/download", methods=["POST"])
def download():
    body = request.json or {}
    # `url` is the specific video's own link. For flat playlists that lack a
    # per-entry link we fall back to the parent URL + playlist index.
    url = (body.get("url") or "").strip()
    parent_url = (body.get("parent_url") or "").strip()
    index = body.get("index")
    quality = body.get("quality", "best")

    target = url or parent_url
    if not target:
        return jsonify({"error": "Missing URL."}), 400

    tmpdir = tempfile.mkdtemp(dir=DOWNLOAD_DIR)
    outtmpl = str(Path(tmpdir) / "%(title).100s.%(ext)s")
    opts = {**base_opts(), "outtmpl": outtmpl, "restrictfilenames": False}

    # If we only have the parent link, restrict the download to this one item.
    if not url and parent_url and index:
        opts["playlist_items"] = str(index)
    else:
        # We have a direct single-video link — never expand it into a playlist.
        opts["noplaylist"] = True

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
            ydl.extract_info(target, download=True)
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": friendly_error(e)}), 400

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


@app.route("/api/diag")
def diag():
    """Diagnostics — tells us WHY YouTube fails on Render without seeing logs.

    Reports: is the PO-token provider process reachable, is the yt-dlp plugin
    loaded, is a proxy set, and does a real YouTube extraction fetch a token.
    Visit /api/diag on the live site.
    """
    import json as _json
    import urllib.request

    out = {"proxy_set": bool(YTDLP_PROXY)}

    # 1) Is the bgutil provider server running inside the container?
    try:
        with urllib.request.urlopen("http://127.0.0.1:4416/ping", timeout=5) as r:
            out["pot_provider"] = _json.loads(r.read().decode())
    except Exception as e:
        out["pot_provider"] = f"UNREACHABLE: {e}"

    # 2) yt-dlp version
    try:
        import yt_dlp
        out["yt_dlp_version"] = yt_dlp.version.__version__
    except Exception as e:
        out["yt_dlp_version"] = f"ERR: {e}"

    # 3) Probe each YouTube player client — find one that slips past the
    #    datacenter-IP bot check without cookies. ?clients=web,tv,ios to override.
    test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
    default_clients = "web_safari,web,tv,tv_embedded,mweb,ios,android,web_embedded"
    clients = [c.strip() for c in
               (request.args.get("clients") or default_clients).split(",") if c.strip()]
    probe = {}
    for c in clients:
        try:
            o = {k: v for k, v in base_opts().items() if k != "extractor_args"}
            o.update({"skip_download": True, "quiet": True, "no_warnings": True})
            o["extractor_args"] = {"youtube": {"player_client": [c]}}
            with YoutubeDL(o) as ydl:
                data = ydl.extract_info(test_url, download=False)
            probe[c] = f"OK ({len(data.get('formats') or [])} formats)"
        except Exception as e:
            probe[c] = "FAIL: " + str(e).splitlines()[0][:90]
    out["client_probe"] = probe
    return jsonify(out)


if __name__ == "__main__":
    print("=" * 55)
    print("  Video / Story Downloader")
    print("  ffmpeg:", FFMPEG_DIR or "NOT FOUND (HD merge may fail)")
    print("  cookies:", "loaded" if COOKIES_FILE.exists() else "none")
    print("  proxy:", YTDLP_PROXY or "none")
    port = int(os.environ.get("PORT", 5000))
    print(f"  Open:   http://127.0.0.1:{port}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False)
