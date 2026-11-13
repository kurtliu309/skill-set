---
name: wide-screenshot-edge-headless
description: When the built-in browser pane is hidden, screenshots only capture the top-left 800px; for wide screenshots use the local headless Edge command directly instead of fiddling repeatedly
status: active
updated: 2026-11-12
---

# wide-screenshot-edge-headless

When the built-in browser pane is hidden (tabs_context will say hidden), screenshots only capture about the top-left 800px, and changing the viewport size does not help. When the pane is visible everything is normal (that is how the earlier rounds worked).

**Why:** on 2026-11-07 I tried repeatedly on this — resizing, panning the page, installing Playwright — and the user felt it was taking too long and reminded me there are many ways to do it.

**How to apply:** when you find the pane is hidden, or the screenshot is wrong, switch immediately to:
`& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --virtual-time-budget=4000 --window-size=1280,760 --screenshot="path.png" http://localhost:PORT/`
(Playwright with the msedge channel fails to start on this machine; downloading Chromium is very slow). Try at most one approach; if it does not work, stop and ask the user.
