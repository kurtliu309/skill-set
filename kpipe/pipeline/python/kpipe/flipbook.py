"""Viewport flipbooks and snapshots.

deliver(): png sequence -> hffmpeg mp4 + key-frame contact sheet in <var_dir>/playblast
           (fallback $HIP/flip):
    <playblast>/seq/$HIPNAME.$F4.png, <playblast>/$HIPNAME.mp4, <playblast>/$HIPNAME_sheet.jpg
snapshot(): current frame of the viewport -> %TEMP%/kpipe_snapshot.png -> clipboard.
"""

import os
import subprocess
import tempfile

import hou

from . import config


def _scene_viewer():
    sv = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if sv is None:
        raise RuntimeError("no Scene Viewer pane")
    return sv


def snapshot(path=None):
    """Flipbook the current frame of the viewport and copy the image to the clipboard."""
    from PySide6 import QtGui, QtWidgets
    sv = _scene_viewer()
    path = path or os.path.join(tempfile.gettempdir(), "kpipe_snapshot.png").replace("\\", "/")
    if os.path.exists(path):
        os.remove(path)
    frame = int(hou.frame())
    s = sv.flipbookSettings().stash()
    s.frameRange((frame, frame))
    s.output(path)
    s.outputToMPlay(False)
    sv.flipbook(sv.curViewport(), s)
    image = QtGui.QImage(path)
    if image.isNull():
        raise RuntimeError("snapshot failed: " + path)
    QtWidgets.QApplication.clipboard().setImage(image)
    hou.ui.setStatusMessage("Snapshot copied to clipboard ({}x{}, frame {})".format(
        image.width(), image.height(), frame))
    return path


def _paths():
    sm = hou.node(config.SM_PATH)
    flip = sm.evalParm("var_" + config.PLAYBLAST) if sm and sm.evalParm("var_dir") else \
        hou.text.expandString("$HIP/flip")
    name = hou.text.expandString("$HIPNAME")
    os.makedirs(flip + "/seq", exist_ok=True)
    return dict(seq=flip + "/seq/" + name + ".$F4.png",
                printf=flip + "/seq/" + name + ".%04d.png",
                frame=lambda f: "{}/seq/{}.{:04d}.png".format(flip, name, int(f)),
                mp4=flip + "/" + name + ".mp4",
                sheet=flip + "/" + name + "_sheet.jpg")


def _range(frange):
    return frange or tuple(int(x) for x in hou.playbar.frameRange())


def mplay_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq mplay.exe"], capture_output=True,
                         creationflags=config.NO_WINDOW).stdout
    return b"mplay.exe" in out


def cleanup():
    """Kill stray mplay / hffmpeg processes (long flipbooks crash with MPlay open)."""
    for exe in ("mplay.exe", "hffmpeg.exe"):
        subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True,
                       creationflags=config.NO_WINDOW)


def viewport_flipbook(frange=None, camera=None, res=None):
    """Interactive session: flipbook the scene viewer, chunked by FLIP_CHUNK frames."""
    sv = _scene_viewer()
    sv.setPwd(hou.node("/obj"))  # inside a geo, other objects get ghosted
    vp = sv.curViewport()
    if camera:
        vp.setCamera(hou.node(camera))
    start, end = _range(frange)
    p = _paths()
    s = sv.flipbookSettings().stash()
    s.output(p["seq"])
    s.outputToMPlay(False)
    if res:
        s.useResolution(True)
        s.resolution(res)
    for a in range(start, end + 1, config.FLIP_CHUNK):
        s.frameRange((a, min(end, a + config.FLIP_CHUNK - 1)))
        sv.flipbook(vp, s)
    return start, end


def opengl_flipbook(frange=None, camera=None):
    """Headless (hython) flipbook through an OpenGL ROP in /out."""
    start, end = _range(frange)
    p = _paths()
    rop = hou.node("/out/kpipe_flip") or hou.node("/out").createNode("opengl", "kpipe_flip")
    rop.parm("trange").set(1)
    rop.parmTuple("f").deleteAllKeyframes()
    rop.parmTuple("f").set((start, end, 1))
    rop.parm("picture").set(p["seq"])
    if camera:
        rop.parm("camera").set(camera)
    rop.render(frame_range=(start, end))
    return start, end


def encode(start, end, fps=None):
    """png sequence -> mp4 with hffmpeg (h264_nvenc, falls back to libx264)."""
    p = _paths()
    ffmpeg = os.path.join(hou.getenv("HFS"), "bin", "hffmpeg.exe")
    fps = fps or hou.fps()
    err = ""
    for codec in ("h264_nvenc", "libx264"):
        cmd = [ffmpeg, "-y", "-framerate", str(fps), "-start_number", str(start),
               "-i", p["printf"], "-frames:v", str(end - start + 1),
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
               "-c:v", codec, "-pix_fmt", "yuv420p", p["mp4"]]
        r = subprocess.run(cmd, capture_output=True, creationflags=config.NO_WINDOW)
        if r.returncode == 0:
            return p["mp4"]
        err = r.stderr.decode(config.CONSOLE_ENCODING, "replace")[-1500:]
    raise RuntimeError("hffmpeg failed:\n" + err)


def contact_sheet(start, end, n=config.SHEET_FRAMES, cols=config.SHEET_COLS,
                  width=config.SHEET_WIDTH):
    """Grid of n evenly spaced frames, <= width px wide, frame numbers burnt in."""
    from PIL import Image, ImageDraw
    p = _paths()
    n = max(1, min(n, end - start + 1))
    frames = [round(start + i * (end - start) / max(1, n - 1)) for i in range(n)]
    frames = [f for f in frames if os.path.exists(p["frame"](f))]
    if not frames:
        raise RuntimeError("no flipbook frames found")
    cols = min(cols, len(frames))
    rows = (len(frames) + cols - 1) // cols
    with Image.open(p["frame"](frames[0])) as im:
        w, h = im.size
    cw = width // cols
    ch = int(h * cw / float(w))
    sheet = Image.new("RGB", (cw * cols, ch * rows), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(frames):
        with Image.open(p["frame"](f)) as im:
            x, y = (i % cols) * cw, (i // cols) * ch
            sheet.paste(im.convert("RGB").resize((cw, ch)), (x, y))
            draw.text((x + 6, y + 4), str(f), fill=(255, 255, 0))
    sheet.save(p["sheet"], quality=90)
    return p["sheet"]


def deliver(frange=None, camera=None, res=None, headless=None):
    """Flipbook + mp4 + contact sheet. Returns dict of output paths."""
    if headless is None:
        headless = not hou.isUIAvailable()
    if headless:
        start, end = opengl_flipbook(frange, camera)
    else:
        start, end = viewport_flipbook(frange, camera, res)
    return dict(mp4=encode(start, end), sheet=contact_sheet(start, end),
                seq=_paths()["seq"], frames=(start, end))
