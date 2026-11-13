#!/usr/bin/env python3
"""Turn a video page into timed plain text. No LLM is called.

Usage:
    python fetch_video.py <url> [--cookies-from-browser edge|firefox|chrome]
                                  [--cookies <cookies.txt>] [--force-asr]
                                  [--model large-v3] [--device auto|cuda|cpu]
                                  [--out <file>]

Order of work:
  1. ask yt-dlp for the page metadata and its subtitles (manual first, then
     automatic; `danmaku` is never treated as a subtitle);
  2. if there is no usable subtitle (or --force-asr), download only the audio
     and transcribe it with faster-whisper (CUDA float16 first on `auto`,
     CPU int8 as fallback).

stdout gets the transcript; progress/diagnostics go to stderr.  Exit code 1 on
failure, with a human-readable reason on stderr.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlparse

import yt_dlp

PREFERRED_LANGS = ["zh-Hans", "zh-CN", "ai-zh", "zh", "zh-Hant", "en"]
SUBTITLE_EXT_ORDER = ["json3", "srt", "vtt", "json"]
ZH_INITIAL_PROMPT = "以下是普通话的句子，使用简体中文。"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(f"[fetch_video] {msg}", file=sys.stderr, flush=True)


def fmt_ts(seconds: float) -> str:
    """Seconds -> mm:ss (minutes keep counting past 59)."""
    s = max(0, int(seconds or 0))
    return f"{s // 60:02d}:{s % 60:02d}"


def fmt_duration(seconds) -> str:
    """Seconds -> mm:ss, or h:mm:ss for videos of an hour or more."""
    s = max(0, int(seconds or 0))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def _join_parts(parts: list[str]) -> str:
    """Join subtitle lines: no space between two CJK characters."""
    out = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if out and not (_is_cjk(out[-1]) and _is_cjk(part[0])):
            out += " "
        out += part
    return re.sub(r"\s+", " ", out).strip()


def _is_cjk(ch: str) -> bool:
    return "\u3400" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" or "\uff00" <= ch <= "\uffef"


# --------------------------------------------------------------------------- #
# Subtitle choice / parsing
# --------------------------------------------------------------------------- #
def _norm_lang(lang: str) -> str:
    return (lang or "").strip().lower().replace("_", "-")


def _find_lang(mapping: dict, lang: str):
    """Exact key, then case-insensitive key, then a key with that prefix."""
    if not mapping:
        return None
    if lang in mapping:
        return mapping[lang]
    want = _norm_lang(lang)
    for key, value in mapping.items():
        if _norm_lang(key) == want:
            return value
    for key, value in mapping.items():
        if _norm_lang(key).startswith(want + "-"):
            return value
    return None


def _choose_entry(entries):
    """Pick the most convenient subtitle format from a metadata entry list."""
    if not entries:
        return None
    if isinstance(entries, dict):
        entries = [entries]
    ranked = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        ext = (item.get("ext") or "").lower()
        if ext == "xml":  # danmaku XML is not a subtitle
            continue
        rank = SUBTITLE_EXT_ORDER.index(ext) if ext in SUBTITLE_EXT_ORDER else len(SUBTITLE_EXT_ORDER)
        ranked.append((rank, item))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
    return ranked[0][1]


def pick_subtitle(subtitles: dict, automatic_captions: dict):
    """Return (kind, lang, entry) where kind is 'manual' or 'auto', or None.

    Priority: manual and automatic tracks are compared in the same preferred
    language order.  `danmaku` (bullet comments) is never a subtitle.
    """
    manual = {k: v for k, v in (subtitles or {}).items()
              if not _norm_lang(k).startswith("danmaku")}
    auto = {k: v for k, v in (automatic_captions or {}).items()
            if not _norm_lang(k).startswith("danmaku")}

    for lang in PREFERRED_LANGS:
        entry = _choose_entry(_find_lang(manual, lang))
        if entry:
            return "manual", lang, entry
        entry = _choose_entry(_find_lang(auto, lang))
        if entry:
            return "auto", lang, entry
    for lang, entries in manual.items():
        entry = _choose_entry(entries)
        if entry:
            return "manual", lang, entry
    for lang, entries in auto.items():
        entry = _choose_entry(entries)
        if entry:
            return "auto", lang, entry
    return None


_SRT_TIME = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
_VTT_TIME = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{1,3})")


def _time_from_match(groups) -> float:
    h, m, s, ms = groups
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(text: str) -> list[tuple[float, float, str]]:
    """Parse SRT or VTT into [(start, end, text)], tags/entities cleaned."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n{2,}", text.strip()):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if lines[0].isdigit():
            lines = lines[1:]
        if not lines:
            continue
        m = _SRT_TIME.search(lines[0])
        if m:
            start, end = _time_from_match(m.groups()[:4]), _time_from_match(m.groups()[4:])
        else:
            m = _VTT_TIME.search(lines[0])
            if not m:
                continue
            g = m.groups()
            start = _time_from_match([g[0], g[1], g[2], g[3]])
            end = _time_from_match([g[4], g[5], g[6], g[7]])
        body = " ".join(lines[1:])
        body = html.unescape(re.sub(r"<[^>]+>", "", body))
        body = _join_parts(body.split())
        if body:
            cues.append((start, end, body))
    return cues


def parse_json3(text: str) -> list[tuple[float, float, str]]:
    """Parse YouTube json3 captions or Bilibili's {"body":[{from,to,content}]}."""
    data = json.loads(text)
    cues = []
    events = data.get("events") if isinstance(data, dict) else None
    if isinstance(events, list):
        for ev in events:
            segs = ev.get("segs") or []
            body = _join_parts([s.get("utf8", "") for s in segs])
            body = re.sub(r"\s+", " ", body.replace("\n", " ")).strip()
            if not body:
                continue
            start = float(ev.get("tStartMs") or 0) / 1000.0
            dur = float(ev.get("dDurationMs") or 0) / 1000.0
            cues.append((start, start + dur, body))
        return cues
    body = data.get("body") if isinstance(data, dict) else None
    if isinstance(body, list):
        for item in body:
            if not isinstance(item, dict):
                continue
            content = _join_parts([str(item.get("content") or "")])
            if not content:
                continue
            start = float(item.get("from") or 0)
            end = float(item.get("to") or start)
            cues.append((start, end, content))
    return cues


def parse_subtitle(text: str, ext: str = "") -> list[tuple[float, float, str]]:
    """Parse a downloaded subtitle blob, sniffing the format when needed."""
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return parse_json3(text)
        except (ValueError, TypeError):
            pass
    if "-->" in text:
        return parse_srt(text)  # parse_srt skips the WEBVTT header block
    return []


def merge_cues(cues, min_span: float = 15.0, max_span: float = 30.0,
               max_gap: float = 2.0) -> list[tuple[float, str]]:
    """Merge adjacent cues into roughly 15-30 second paragraphs."""
    groups = []
    cur = None  # [start, end, [texts]]
    for start, end, text in sorted(cues, key=lambda c: (c[0], c[1])):
        text = (text or "").strip()
        if not text:
            continue
        end = max(end, start)
        if cur is None:
            cur = [start, end, [text]]
        elif start - cur[1] <= max_gap and start - cur[0] <= max_span:
            cur[1] = max(cur[1], end)
            cur[2].append(text)
        else:
            groups.append(cur)
            cur = [start, end, [text]]
        if cur[1] - cur[0] >= min_span:
            groups.append(cur)
            cur = None
    if cur is not None:
        groups.append(cur)
    return [(g[0], _join_parts(g[2])) for g in groups]


# --------------------------------------------------------------------------- #
# yt-dlp setup
# --------------------------------------------------------------------------- #
def find_ffmpeg() -> str | None:
    """Directory containing ffmpeg.exe, or None.  Read-only search.

    yt-dlp's ffmpeg downloader checks PATH and ignores ffmpeg_location when
    deciding whether ffmpeg exists, so the directory is prepended to PATH here
    (this process only).
    """
    candidates = []
    on_path = shutil.which("ffmpeg")
    if on_path:
        candidates.append(os.path.dirname(on_path))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "VideoDownloader", "bin"))
    extra = os.environ.get("VIDEODOWNLOADER_DIR")
    if extra and os.path.isdir(extra):
        candidates += [os.path.dirname(m) for m in
                       glob.glob(os.path.join(extra, "**", "ffmpeg.exe"), recursive=True)]
    for directory in candidates:
        exe = os.path.join(directory, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(exe):
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            if directory not in path_parts:
                os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
            try:
                from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
                cache = FFmpegPostProcessor._version_cache
                for key in [k for k, v in cache.items() if k is not None and not v]:
                    cache.pop(key, None)
            except Exception:
                pass
            return directory
    return None


def build_opts(cookies_from_browser: str | None, cookies: str | None,
               ffmpeg_dir: str | None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "noprogress": True,
    }
    if cookies:
        opts["cookiefile"] = cookies
    elif cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser, None, None, None)
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir
    return opts


def _is_bilibili(url: str, info: dict) -> bool:
    extractor = (info.get("extractor") or "").lower()
    return "bilibili" in extractor or "bilibili.com" in (url or "").lower()


def _single_entry(info: dict) -> dict:
    """If yt-dlp still handed back a playlist, take the first / requested part."""
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            return entries[0]
    return info


def _normalized_url(url: str, info: dict) -> str:
    final = info.get("webpage_url") or url
    p = parse_qs(urlparse(url).query).get("p")
    if p and "bilibili.com" in final and "?p=" not in final:
        final = final.split("?")[0] + f"?p={p[0]}"
    return final


# --------------------------------------------------------------------------- #
# Subtitle path
# --------------------------------------------------------------------------- #
def download_subtitle(entry: dict, opts: dict) -> str | None:
    """Return subtitle text. Entries may carry inline `data` or a URL."""
    data = entry.get("data")
    if isinstance(data, str) and data.strip():
        return data
    url = entry.get("url")
    if not url:
        return None
    with yt_dlp.YoutubeDL(opts) as ydl:
        resp = ydl.urlopen(url)
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# ASR path
# --------------------------------------------------------------------------- #
def download_audio(url: str, opts: dict, tmpdir: str, is_bili: bool,
                   ffmpeg_dir: str | None) -> str:
    """Download only the audio track into tmpdir; return its path."""
    o = dict(opts)
    o.update({
        "skip_download": False,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
        "paths": {"home": tmpdir},
        "writesubtitles": False,
        "writeautomaticsub": False,
    })
    if is_bili and ffmpeg_dir:
        # Bilibili CDNs answer yt-dlp's native range requests with HTTP 567;
        # plain ffmpeg HTTP requests work.
        o["external_downloader"] = "ffmpeg"
    with yt_dlp.YoutubeDL(o) as ydl:
        info = _single_entry(ydl.extract_info(url, download=True))
    for dl in info.get("requested_downloads") or []:
        path = dl.get("filepath")
        if path and os.path.isfile(path):
            return path
    candidates = [p for p in glob.glob(os.path.join(tmpdir, "audio.*"))
                  if not p.endswith((".part", ".ytdl"))]
    if candidates:
        return candidates[0]
    raise RuntimeError("audio download finished but no output file was found")


def _language_from_metadata(info: dict) -> str | None:
    lang = info.get("language")
    if not isinstance(lang, str) or not lang.strip():
        return None
    lang = lang.strip().lower().replace("_", "-").split("-")[0]
    return lang or None


def _add_cuda_dll_dirs() -> None:
    """Make pip-installed nvidia-*-cu12 DLLs visible to ctranslate2 on Windows.

    CTranslate2 loads cublas/cudnn with LoadLibrary, which does not look inside
    site-packages/nvidia/*/bin by itself.  Must run before faster_whisper (and
    therefore ctranslate2) is imported.
    """
    try:
        import importlib.util
        import site
        from pathlib import Path

        roots = []
        spec = importlib.util.find_spec("nvidia")
        if spec and spec.submodule_search_locations:
            roots = list(spec.submodule_search_locations)
        if not roots:
            for sp in site.getsitepackages():
                cand = Path(sp) / "nvidia"
                if cand.is_dir():
                    roots.append(str(cand))
        for root in roots:
            for bin_dir in Path(root).glob("*/bin"):
                if not bin_dir.is_dir():
                    continue
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                try:
                    os.add_dll_directory(str(bin_dir))
                except (AttributeError, OSError):
                    pass
    except Exception:
        pass


def transcribe(audio_path: str, model_name: str, device: str,
               preferred_language: str | None = None):
    """Run faster-whisper. Returns (cues, used_device, language, elapsed)."""
    if device in ("auto", "cuda"):
        _add_cuda_dll_dirs()
    from faster_whisper import WhisperModel

    if device == "auto":
        attempts = [("cuda", "float16"), ("cpu", "int8")]
    elif device == "cuda":
        attempts = [("cuda", "float16")]
    else:
        attempts = [("cpu", "int8")]

    last_error = None
    for idx, (dev, compute_type) in enumerate(attempts):
        started = time.time()
        try:
            model = WhisperModel(model_name, device=dev, compute_type=compute_type)
            language, segments = _run_model(model, audio_path, preferred_language)
            elapsed = time.time() - started
            if idx > 0:
                log(f"fell back to {dev}/{compute_type} (reason above)")
            return segments, dev, language, elapsed
        except Exception as e:  # CUDA kernels, cuBLAS missing, OOM, ...
            last_error = e
            if idx + 1 < len(attempts):
                log(f"{dev}/{compute_type} unavailable: {type(e).__name__}: {e}; "
                    "switching to CPU int8")
                continue
            raise
    raise last_error  # pragma: no cover


def _decode_audio_fallback(path: str):
    """Decode to 16 kHz mono float32 when faster-whisper's decode_audio breaks.

    faster-whisper 1.2.1 calls `av.open(..., metadata_errors="ignore")`, which
    PyAV 19 no longer accepts; this does the same job with the current API.
    """
    import av
    import numpy as np

    with av.open(path) as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise RuntimeError("the file has no audio track")
        stream.thread_type = "AUTO"
        resampler = av.audio.resampler.AudioResampler(
            format="flt", layout="mono", rate=16000)
        chunks = []
        for frame in container.decode(stream):
            chunks.extend(resampler.resample(frame) or [])
        chunks.extend(resampler.resample(None) or [])
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate([c.to_ndarray().reshape(-1) for c in chunks]).astype(np.float32)


def _run_model(model, audio_path: str, preferred_language: str | None = None):
    """Decode once, detect the language, transcribe."""
    try:
        from faster_whisper.audio import decode_audio
        audio = decode_audio(audio_path, sampling_rate=16000)
    except Exception:
        try:
            audio = _decode_audio_fallback(audio_path)
        except Exception as e2:
            raise RuntimeError(f"audio decoding failed: {e2}") from e2

    language = preferred_language
    if not language and not isinstance(audio, str):
        try:
            lang, prob, _ = model.detect_language(audio, vad_filter=True)
            if lang and prob and prob >= 0.5:
                language = lang
        except Exception:
            language = None

    kwargs = {"vad_filter": True}
    if language:
        kwargs["language"] = language
        if _norm_lang(language).startswith("zh"):
            kwargs["initial_prompt"] = ZH_INITIAL_PROMPT
    segments, info = model.transcribe(audio, **kwargs)
    detected = language or getattr(info, "language", None)
    cues = [(float(s.start), float(s.end), s.text.strip()) for s in segments]
    return detected, cues


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def format_output(title: str, url: str, uploader: str, duration,
                  source: str, cues) -> str:
    merged = merge_cues(cues)
    lines = [
        f"# {title or '(untitled)'}",
        f"- URL: {url}",
        f"- Uploader / channel: {uploader or 'unknown'}",
        f"- Duration: {fmt_duration(duration)}",
        f"- Text source: {source}",
        "",
    ]
    for start, text in merged:
        lines.append(f"[{fmt_ts(start)}] {text}")
    return "\n".join(lines).rstrip() + "\n"


def explain_error(err: Exception) -> str:
    low = str(err).lower()
    if "cookie database" in low or "could not copy" in low or "decrypt" in low and "cookie" in low:
        return ("Cannot read the browser cookies (a running browser locks its cookie database). "
                "Fully close Edge/Chrome/Firefox and retry, or export cookies.txt and use --cookies.")
    if "deleted or geo-restricted" in low or "truecode" in low or "404" in low:
        return ("The video does not exist, was deleted, or is not playable in your region "
                "(Bilibili returned 404).")
    if any(k in low for k in ("login", "sign in", "members-only", "private video", "subscription")):
        return "This video needs a login or a membership; add --cookies-from-browser or --cookies."
    if any(k in low for k in ("geo", "region", "country", "blocked")):
        return "Region-restricted: this video is not playable in your region."
    if any(k in low for k in ("timed out", "timeout", "connection", "network",
                              "getaddrinfo", "unable to download webpage", "reset")):
        return "Network error: connection failed or timed out; try again later."
    if "unsupported url" in low:
        return "Unsupported link: yt-dlp does not recognize this site."
    if any(k in low for k in ("cublas", "cudnn", "cuda", "compute_type", "float16")):
        return "CUDA unavailable: use --device cpu, or --device auto to fall back to CPU."
    if any(k in low for k in ("audio decoding", "no audio", "produced no text",
                              "no output file")):
        return "Audio fetching or transcription failed (see the original error)."
    return "Download failed."


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def run(args) -> int:
    ffmpeg_dir = find_ffmpeg()
    if not ffmpeg_dir:
        log("ffmpeg.exe not found; Bilibili audio will use yt-dlp's native downloader "
            "(may hit HTTP 567)")
    opts = build_opts(args.cookies_from_browser, args.cookies, ffmpeg_dir)

    # --- metadata (+ subtitles when writesubtitles is on) ------------------
    info = None
    try:
        with yt_dlp.YoutubeDL({**opts, "writesubtitles": not args.force_asr}) as ydl:
            info = _single_entry(ydl.extract_info(args.url, download=False))
    except Exception as e:
        if args.force_asr or "cookie database" in str(e).lower() \
                or "could not copy" in str(e).lower():
            raise
        log(f"metadata extraction with subtitles failed; retrying without the subtitle "
            f"request: {type(e).__name__}")
        try:
            with yt_dlp.YoutubeDL({**opts, "writesubtitles": False}) as ydl:
                info = _single_entry(ydl.extract_info(args.url, download=False))
        except Exception:
            raise

    title = info.get("title") or "(untitled)"
    up = info.get("uploader") or info.get("channel") or info.get("creator") or ""
    url = _normalized_url(args.url, info)

    # --- subtitles ---------------------------------------------------------
    chosen = None if args.force_asr else pick_subtitle(
        info.get("subtitles"), info.get("automatic_captions"))
    if chosen:
        kind, lang, entry = chosen
        try:
            raw = download_subtitle(entry, opts)
            cues = parse_subtitle(raw or "", entry.get("ext") or "")
            if cues:
                source = f"subtitles ({lang})"
                duration = info.get("duration") or cues[-1][1]
                text = format_output(title, url, up, duration, source, cues)
                write_output(text, args.out)
                return 0
            log(f"subtitles ({lang}) parsed to nothing; using transcription")
        except Exception as e:
            log(f"subtitle download/parse failed ({type(e).__name__}: {e}); "
                "using transcription")
    elif not args.force_asr:
        log("no usable subtitles; using transcription")

    # --- ASR ---------------------------------------------------------------
    is_bili = _is_bilibili(args.url, info)
    meta_language = _language_from_metadata(info)
    with tempfile.TemporaryDirectory(prefix="fetch_video_") as tmpdir:
        audio = download_audio(args.url, opts, tmpdir, is_bili, ffmpeg_dir)
        cues, device, language, elapsed = transcribe(
            audio, args.model, args.device, meta_language)
    if not cues:
        raise RuntimeError("transcription produced no text")

    source = f"transcription ({args.model}, {device}, {elapsed:.0f}s)"
    duration = info.get("duration") or (max(c[1] for c in cues) if cues else 0)
    text = format_output(title, url, up, duration, source, cues)
    write_output(text, args.out)
    return 0


def write_output(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        log(f"wrote {out}")
    else:
        sys.stdout.write(text)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description="Video to text (subtitles first, faster-whisper transcription otherwise).")
    ap.add_argument("url")
    ap.add_argument("--cookies-from-browser", choices=["edge", "firefox", "chrome"],
                    help="read cookies from a browser (the browser must be closed)")
    ap.add_argument("--cookies", help="path to cookies.txt")
    ap.add_argument("--force-asr", action="store_true",
                    help="ignore subtitles and force transcription")
    ap.add_argument("--model", default="large-v3",
                    help="faster-whisper model (default large-v3)")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    ap.add_argument("--out", help="write to a file instead of stdout")
    args = ap.parse_args(argv)
    args.url = args.url.strip()

    if args.cookies and args.cookies_from_browser:
        print("[fetch_video] --cookies and --cookies-from-browser are mutually exclusive",
              file=sys.stderr)
        return 1
    try:
        return run(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        reason = explain_error(e)
        detail = str(e).strip().splitlines()
        last = detail[-1] if detail else type(e).__name__
        print(f"[fetch_video] failed: {reason}", file=sys.stderr)
        print(f"[fetch_video] original error: {last}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
