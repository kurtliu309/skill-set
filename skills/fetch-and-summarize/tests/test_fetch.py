"""Offline tests: subtitle choice/parsing, merging, HTML-to-text, truncation.

Run with:  py -m pytest -q tests
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_page  # noqa: E402
import fetch_video  # noqa: E402


# --------------------------------------------------------------------------- #
# Subtitle priority
# --------------------------------------------------------------------------- #
def _entry(ext="srt", data="1\n00:00:00,000 --> 00:00:01,000\nx\n"):
    return [{"ext": ext, "data": data}]


def test_preferred_language_order_across_manual_and_auto():
    subs = {"danmaku": [{"ext": "xml", "url": "https://example/danmaku.xml"}],
            "en": _entry()}
    autos = {"ai-zh": _entry(), "en": _entry()}
    kind, lang, _ = fetch_video.pick_subtitle(subs, autos)
    assert (kind, lang) == ("auto", "ai-zh")


def test_zh_cn_auto_beats_zh_hant_manual():
    kind, lang, _ = fetch_video.pick_subtitle(
        {"zh-Hant": _entry()}, {"zh-CN": _entry()})
    assert (kind, lang) == ("auto", "zh-CN")


def test_manual_wins_over_auto_for_same_language():
    kind, lang, _ = fetch_video.pick_subtitle({"zh-Hans": _entry()}, {"zh-Hans": _entry()})
    assert (kind, lang) == ("manual", "zh-Hans")


def test_danmaku_never_counts_as_subtitle():
    assert fetch_video.pick_subtitle(
        {"danmaku": [{"ext": "xml", "url": "x"}]},
        {"danmaku": [{"ext": "xml", "url": "x"}]}) is None


def test_danmaku_skipped_when_falling_back():
    kind, lang, _ = fetch_video.pick_subtitle(
        {"danmaku": [{"ext": "xml", "url": "x"}], "fr": _entry()},
        {"danmaku": [{"ext": "xml", "url": "x"}]})
    assert (kind, lang) == ("manual", "fr")


def test_other_language_takes_first_available():
    kind, lang, _ = fetch_video.pick_subtitle({"ja": _entry(), "ko": _entry()}, {})
    assert (kind, lang) == ("manual", "ja")


def test_subtitle_format_preference():
    entries = [{"ext": "vtt", "data": "x"}, {"ext": "json3", "data": "{}"}]
    pick = fetch_video._choose_entry(entries)
    assert pick["ext"] == "json3"


# --------------------------------------------------------------------------- #
# Subtitle parsing
# --------------------------------------------------------------------------- #
def test_parse_srt_multiline_tags_and_cjk_join():
    srt = (
        "﻿1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "你好\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,200\n"
        "<i>世界</i>\n"
        "第二行\n"
    )
    cues = fetch_video.parse_srt(srt)
    assert cues[0] == (1.0, 3.5, "你好")
    assert cues[1][0] == 4.0 and cues[1][1] == 6.2
    assert cues[1][2] == "世界第二行"


def test_parse_srt_english_lines_join_with_space():
    srt = "1\n00:00:00,000 --> 00:00:02,000\nhello\nworld\n"
    assert fetch_video.parse_srt(srt) == [(0.0, 2.0, "hello world")]


def test_parse_json3_youtube_and_bilibili():
    youtube = ('{"events": ['
               '{"tStartMs": 0, "dDurationMs": 2000, "segs": [{"utf8": "Hello "}, {"utf8": "world"}]},'
               '{"tStartMs": 2500, "segs": [{"utf8": "\\n"}]},'
               '{"tStartMs": 3000, "dDurationMs": 1000, "segs": [{"utf8": "Bye"}]}]}')
    assert fetch_video.parse_json3(youtube) == [(0.0, 2.0, "Hello world"), (3.0, 4.0, "Bye")]
    bili = '{"body": [{"from": 1.2, "to": 3.4, "content": "第一句"}]}'
    assert fetch_video.parse_json3(bili) == [(1.2, 3.4, "第一句")]


def test_parse_subtitle_sniffs_format():
    json3 = '{"events": [{"tStartMs": 0, "dDurationMs": 1000, "segs": [{"utf8": "hi"}]}]}'
    assert fetch_video.parse_subtitle(json3) == [(0.0, 1.0, "hi")]
    srt = "1\n00:00:00,000 --> 00:00:01,000\nhi\n"
    assert fetch_video.parse_subtitle(srt) == [(0.0, 1.0, "hi")]
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhi\n"
    assert fetch_video.parse_subtitle(vtt) == [(1.0, 2.0, "hi")]


# --------------------------------------------------------------------------- #
# Formatting / merging
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"), (5, "00:05"), (65, "01:05"), (12.9, "00:12"), (3600, "60:00"),
])
def test_timestamp_format(seconds, expected):
    assert fetch_video.fmt_ts(seconds) == expected


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"), (65, "01:05"), (3661, "1:01:01"),
])
def test_duration_format(seconds, expected):
    assert fetch_video.fmt_duration(seconds) == expected


def test_merge_cues_groups_into_15_to_30_seconds():
    cues = [(i * 5, i * 5 + 4, f"s{i}") for i in range(12)]
    groups = fetch_video.merge_cues(cues)
    assert [int(g[0]) for g in groups] == [0, 20, 40]
    assert groups[0][1] == "s0 s1 s2 s3"


def test_merge_cues_keeps_a_silence_break():
    groups = fetch_video.merge_cues([(0, 2, "a"), (10, 12, "b")])
    assert groups == [(0, "a"), (10, "b")]


def test_merge_cues_long_single_cue():
    assert fetch_video.merge_cues([(0, 40, "long")]) == [(0, "long")]


def test_format_output_header_and_lines():
    text = fetch_video.format_output(
        "Title", "https://example/v", "Author", 65, "subtitles (zh-Hans)",
        [(0, 2, "第一句"), (2, 4, "第二句")])
    lines = text.splitlines()
    assert lines[0] == "# Title"
    assert lines[1] == "- URL: https://example/v"
    assert lines[2] == "- Uploader / channel: Author"
    assert lines[3] == "- Duration: 01:05"
    assert lines[4] == "- Text source: subtitles (zh-Hans)"
    assert lines[6] == "[00:00] 第一句第二句"


def test_normalized_url_keeps_requested_part():
    assert fetch_video._normalized_url(
        "https://www.bilibili.com/video/BV1x?p=2",
        {"webpage_url": "https://www.bilibili.com/video/BV1x"}) == \
        "https://www.bilibili.com/video/BV1x?p=2"
    assert fetch_video._normalized_url(
        "https://www.bilibili.com/video/BV1x",
        {"webpage_url": "https://www.bilibili.com/video/BV1x"}) == \
        "https://www.bilibili.com/video/BV1x"


def test_build_opts_uses_one_playlist_and_browser_cookies():
    opts = fetch_video.build_opts("edge", None, None)
    assert opts["noplaylist"] is True
    assert opts["cookiesfrombrowser"] == ("edge", None, None, None)
    assert "cookiefile" not in opts


def test_explain_error_classifies_common_failures():
    assert "deleted" in fetch_video.explain_error(
        Exception("ERROR: [BiliBili] This video may be deleted or geo-restricted"))
    assert "cookies" in fetch_video.explain_error(
        Exception("ERROR: Could not copy Chrome cookie database"))


# --------------------------------------------------------------------------- #
# fetch_page helpers
# --------------------------------------------------------------------------- #
def test_html_to_text_skips_scripts_nav_footer():
    raw = ("<html><head><title>T &amp; X</title><style>p{}</style></head><body>"
           "<nav>menu</nav><h1>Hi</h1><p>Hello <b>world</b></p>"
           "<script>bad()</script><footer>foot</footer></body></html>")
    title, text = fetch_page.html_to_text(raw)
    assert title == "T & X"
    assert "Hi" in text and "Hello world" in text
    assert "menu" not in text and "bad()" not in text and "foot" not in text


def test_github_raw():
    assert fetch_page.github_raw(
        "https://github.com/u/r/blob/main/a/b.md?plain=1") == \
        "https://raw.githubusercontent.com/u/r/main/a/b.md?plain=1"
    assert fetch_page.github_raw("https://example.com/x") == "https://example.com/x"


def test_truncate_and_render_note():
    text, truncated, original = fetch_page.truncate("abcdefghij", 5)
    assert (text, truncated, original) == ("abcde", True, 10)
    out = fetch_page.render("T", "https://e/x", "abcdefghij", 5)
    assert out.startswith("# T\n- URL: https://e/x\n\nabcde")
    assert "(truncated; the original was about 10 characters)" in out


def test_render_keeps_short_text_whole():
    out = fetch_page.render("T", "https://e/x", "  hi  ", 100)
    assert out.endswith("hi\n")
    assert "truncated" not in out
