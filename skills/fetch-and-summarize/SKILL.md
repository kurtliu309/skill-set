---
name: fetch-and-summarize
description: Turn a video (Bilibili, YouTube and any other site yt-dlp supports) or a web page into plain text with timestamps, which you then summarize, analyze and answer questions from. Use it whenever someone pastes a video or web link and wants to know "what does it say", "summarize this", "is this video worth watching", "what was said at minute N", or "read this for me"; it is especially necessary when you cannot watch video yourself or WebFetch cannot get the body text. The scripts only fetch; summarizing is your job.
---

# fetch-and-summarize

Two scripts: fetch the text, then you read it. They call no model and do nothing else on the network.

Use a Python environment with the dependencies in `requirements.txt`. Below, `PY` refers to that interpreter (for example `<VENV>/Scripts/python.exe`). The scripts live in this skill directory.

## Video

```
PY fetch_video.py <url> [--cookies-from-browser edge|firefox|chrome] [--cookies <cookies.txt>]
                     [--force-asr] [--model large-v3] [--device auto|cuda|cpu] [--out <file>]
```

The order of work is:
1. Look for subtitles first (uploader-provided / platform AI captions, Chinese preferred, bullet comments do not count). If there are any, use them; it takes seconds.
2. Otherwise download only the audio and transcribe it locally with faster-whisper (falls back to CPU when no GPU is available).
3. Output: title, link, uploader, duration, a "text source" line, then `[mm:ss] a paragraph`, roughly one paragraph per 15–30 seconds.

A link with `?p=N` fetches only part N; otherwise only part 1 is fetched.

**How to choose options**
- Many Bilibili subtitles require a login. Run without cookies first; if the output says "transcription" but you think the video should have subtitles, add `--cookies-from-browser`.
- Long videos take time to transcribe: `large-v3` is the most accurate and downloads about 3 GB of model on first use. For very long videos (>1 hour), or when you only need the gist quickly, use `--model medium` or `small`.
- Transcription uses about 4–5 GB of VRAM; another GPU-heavy app (for example Houdini) can take it. If you get an out-of-memory error, add `--device cpu --model small`.
- The result is long. Use `--out` to write it to a scratch file and read it in sections; don't stuff tens of thousands of characters into the context.

## Web pages

```
PY fetch_page.py <url> [--max-chars 30000] [--out <file>]
```

Converts HTML to plain text. GitHub `blob` links are automatically fetched as raw. Oversized text is truncated with a note showing the original length.

## After you have the text

- Say where the text came from: subtitles or transcription. Transcriptions contain misheard and homophone errors; when quoting, say it is a "transcript".
- Give the timestamps for key points so the user can jump straight to them.
- Do not invent content that is not in the text. Things visible on screen (code, charts, demos) are not in the transcript; when they matter, say "you need to watch this part".

## Pitfalls

- **Locked cookies**: Chrome / Edge lock their cookie database while running, so `--cookies-from-browser` fails. Have the user close that browser, or export a `cookies.txt` and use `--cookies`. Never print or save cookie contents.
- **Do not hit Bilibili concurrently**: concurrent requests fail. Fetch one at a time.
- **ffmpeg**: the script looks for `ffmpeg.exe` on `PATH`, then under `%APPDATA%\VideoDownloader\bin`, then under the directory named by the `VIDEODOWNLOADER_DIR` environment variable, and prepends it to `PATH` temporarily (yt-dlp's Bilibili downloader only checks `PATH`, not `ffmpeg_location`, and otherwise reports error 567).
- **CUDA DLLs**: the script prepends `site-packages/nvidia/*/bin` inside the venv to `PATH`; otherwise it fails with `cublas64_12.dll is not found`.
- **PyAV version**: PyAV 19 removed an argument that faster-whisper 1.2.1 uses; the script has a fallback decoder. Remove the fallback after upgrading faster-whisper.
- **Dead video**: Bilibili returning `-404` ("where did the video go") means the video was deleted. The script exits 1; ask the user for another link.

## Tests

```
PY -m pytest -q tests
```

Offline tests, no network. Run them after changing the scripts.
