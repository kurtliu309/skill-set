#!/usr/bin/env python3
"""Fetch one web page and print its readable text. No LLM is called.

Usage:
    python fetch_page.py <url> [--max-chars 30000] [--out <file>]

HTML is reduced to plain text (scripts/styles/nav/footer/header/form dropped),
GitHub blob links are fetched as raw, and plain text / markdown / JSON are
passed through unchanged.  Exit code 1 and a message on stderr on failure.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

MAX_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 10
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Extensions we are willing to print verbatim (when the server sends a generic
# content-type).  `.html`/`.htm` are handled by the HTML path below.
TEXT_EXT = {
    "txt", "md", "markdown", "csv", "tsv", "json", "yaml", "yml", "log", "ini",
    "toml", "xml", "py", "js", "ts", "jsx", "tsx", "sh", "bat", "ps1", "cmd",
    "c", "h", "cpp", "hpp", "cc", "cs", "java", "go", "rs", "lua", "sql", "css",
    "glsl", "hlsl", "osl", "usda", "vfl", "vex",
}
HTML_EXT = {"html", "htm"}


class TextOnly(HTMLParser):
    """Collect the visible text of an HTML document (ported from fetcher.py)."""

    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6",
             "tr", "pre", "article", "section"}

    def __init__(self):
        super().__init__()
        self.out, self.title, self._skip, self._in_title = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.out.append(data)

    def text(self):
        t = re.sub(r"[ \t\r\f\v]+", " ", "".join(self.out))
        return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def html_to_text(raw: str) -> tuple[str, str]:
    """HTML string -> (title, plain text)."""
    p = TextOnly()
    p.feed(raw)
    return re.sub(r"\s+", " ", p.title).strip(), p.text()


def github_raw(url: str) -> str:
    """github.com/<u>/<r>/blob/<path> -> raw.githubusercontent.com/..."""
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$", url)
    if not m:
        return url
    return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"


def truncate(text: str, max_chars: int) -> tuple[str, bool, int]:
    """Return (text, truncated, original_length)."""
    if max_chars <= 0:
        max_chars = 30000
    n = len(text)
    return (text[:max_chars], True, n) if n > max_chars else (text, False, n)


def decode_body(data: bytes, content_type: str) -> str:
    """Decode bytes using the charset from the header, then UTF-8, then GB18030."""
    encodings = []
    m = re.search(r"charset\s*=\s*\"?([\w.-]+)", content_type or "", re.I)
    if m:
        encodings.append(m.group(1))
    encodings += ["utf-8", "gb18030"]
    seen = set()
    for enc in encodings:
        if enc.lower() in seen:
            continue
        seen.add(enc.lower())
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _is_html(content_type: str, path_ext: str, data: bytes) -> bool:
    ctype = (content_type or "").lower()
    if "html" in ctype:
        return True
    if path_ext in HTML_EXT:
        return True
    if not ctype or ctype.startswith("application/octet-stream"):
        head = data.lstrip()[:512].lower()
        return head.startswith(b"<!doctype html") or head.startswith(b"<html")
    return False


def _is_text(content_type: str, path_ext: str) -> bool:
    ctype = (content_type or "").lower()
    if path_ext in TEXT_EXT:
        return True
    if ctype.startswith("text/"):
        return True
    if any(t in ctype for t in ("json", "xml", "javascript", "x-markdown", "x-yaml")):
        return True
    return not ctype


def render(title: str, url: str, text: str, max_chars: int) -> str:
    """Header + body, with the truncation note at the end."""
    text, truncated, original = truncate(text.strip(), max_chars)
    lines = [f"# {title or '(untitled)'}", f"- URL: {url}", ""]
    lines.append(text)
    if truncated:
        lines.append("")
        lines.append(f"(truncated; the original was about {original} characters)")
    return "\n".join(lines).rstrip() + "\n"


def fetch(url: str) -> tuple[str, str, str, bool]:
    """Download url. Returns (final_url, content_type, body_text, is_html)."""
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("only http(s) URLs are supported")
    with httpx.Client(timeout=20, follow_redirects=True, max_redirects=MAX_REDIRECTS,
                      headers={"User-Agent": UA,
                               "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}) as client:
        with client.stream("GET", url) as r:
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}")
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > MAX_BYTES:
                    raise RuntimeError("content is larger than 10 MB; giving up")
            data = bytes(buf)
            ctype = r.headers.get("content-type", "")
            final = str(r.url)
    path_ext = urlparse(final).path.rsplit(".", 1)[-1].lower() if "." in urlparse(final).path else ""
    body = decode_body(data, ctype)
    if _is_html(ctype, path_ext, data):
        return final, ctype, body, True
    if _is_text(ctype, path_ext):
        return final, ctype, body, False
    if b"\x00" in data[:4096]:
        raise RuntimeError(f"unsupported binary content ({ctype or 'unknown type'}); "
                           "only web pages and text are supported")
    return final, ctype, body, False


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Fetch a web page and print plain text (no LLM).")
    ap.add_argument("url")
    ap.add_argument("--max-chars", type=int, default=30000,
                    help="maximum number of body characters (default 30000)")
    ap.add_argument("--out", help="write to a file instead of stdout")
    args = ap.parse_args(argv)

    try:
        final_url, ctype, body, is_html = fetch(github_raw(args.url.strip()))
        path_ext = urlparse(final_url).path.rsplit(".", 1)[-1].lower() \
            if "." in urlparse(final_url).path else ""
        if is_html:
            title, text = html_to_text(body)
        else:
            title, text = "", body
            if not title:
                name = urlparse(final_url).path.rsplit("/", 1)[-1]
                title = name or (urlparse(final_url).hostname or "")
                if path_ext in ("md", "markdown"):
                    first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
                    if first.startswith("#"):
                        title = first.lstrip("#").strip() or title
        out = render(title, args.url.strip(), text, args.max_chars)
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(out)
            print(f"[fetch_page] wrote {args.out}", file=sys.stderr)
        else:
            sys.stdout.write(out)
        return 0
    except Exception as e:
        print(f"[fetch_page] fetch failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
