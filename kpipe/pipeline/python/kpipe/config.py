"""Pipeline constants.

    projects/<project>/project.json    {"created": ..., "shots": {"GRS_0010": {"start": 1001, "end": 1020}},
                                                        "assets": {"fxGrass": {"start": 1, "end": 100}}}
    projects/<project>/shot/<SEQ>/<SHOT>/{scenes,cache,playblast,assets,render}
    projects/<project>/asset/<category>/<asset>/{scenes,cache,playblast,assets,render}
        asset code = category + Name, e.g. fxGrass (category fx)
    hip: <SHOT or asset>_v001_<artist>.hip in scenes/
"""

import os

# <pipeline>/python/kpipe/config.py -> <pipeline>
PIPELINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
_BASE = os.path.dirname(PIPELINE)  # the folder that holds pipeline/
ROOT = os.environ.get("KPIPE_ROOT", _BASE + "/projects")  # set KPIPE_ROOT to keep projects elsewhere
PLAYGROUND = os.environ.get("KPIPE_PLAYGROUND", _BASE + "/playground")  # test projects
MANIFEST = "project.json"

# Subfolders of every shot / asset folder; each one has a Scene Manager variable var_<name>.
ITEM_DIRS = ("scenes", "cache", "playblast", "assets", "render")
SCENES = "scenes"        # work files (hips)
PLAYBLAST = "playblast"  # flipbooks
ASSET_CATEGORIES = ("fx", "env", "model", "char", "prop")  # Create window defaults; others may be typed
DEFAULT_RANGE = (1001, 1100)

DEFAULT_ARTIST = "artist"  # Scene Manager / Create window default
MCP_ARTIST = "mcp"       # pass artist=MCP_ARTIST from MCP sessions

# Scene Manager HDA.
SM_TYPE = "kpipe::scene_manager::1.0"
SM_NAME = "scene_manager"
SM_PATH = "/obj/" + SM_NAME
SM_HDA = PIPELINE + "/otls/kpipe_scene_manager.hda"

# Shot Value SOP HDA.
SV_TYPE = "kpipe::shot_value::1.0"
SV_HDA = PIPELINE + "/otls/kpipe_shot_value.hda"

# Testing-phase limits.
CACHE_LIMIT_GB = 2.0
TEST_FRAMES = 15

# Flipbook / delivery.
FLIP_CHUNK = 150
SHEET_WIDTH = 1280
SHEET_FRAMES = 8
SHEET_COLS = 4

NO_WINDOW = 0x08000000  # subprocess creationflags: don't pop a console
CONSOLE_ENCODING = "gbk"
