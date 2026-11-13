# kpipe

A Houdini pipeline toolkit: projects, shots and assets with a fixed folder layout,
a Scene Manager node whose live variables follow the current shot, versioned work
files, per-shot caching and TOP wedges, a Shot Value SOP, and flipbook delivery.

This folder is the toolkit itself (scripts and components). How to use it with Claude
lives in the skill `skills/houdini-kpipe/` (naming and paths) and
`skills/houdini-mcp-conventions/` (working rules over the Houdini MCP server).

## Layout

```
kpipe/
└── pipeline/
    ├── kpipe.json              Houdini package file (set KPIPE to this pipeline folder)
    ├── python/kpipe/           the Python package (config, project, scene, cache, tops, ...)
    ├── otls/                   kpipe_scene_manager.hda, kpipe_shot_value.hda
    ├── toolbar/kpipe.shelf     the KPipe shelf
    └── tools/hou_exec.py       run code inside a live Houdini session (port 8100)
```

## Install

1. Copy `pipeline/` anywhere, e.g. `<HOUDINI>/pipeline`.
2. Edit `kpipe.json`: replace `<PATH-TO>/pipeline` with the real path, then copy it to
   `Documents/houdiniXX.X/packages/`.
3. Start Houdini. The KPipe shelf appears and the HDAs in `otls/` load. To regenerate them, run
   `kpipe.scene.build_hda()` and `kpipe.shot_value.build_hda()`.

Projects are created under `<folder that holds pipeline>/projects`. Set `KPIPE_ROOT`
(projects) and `KPIPE_PLAYGROUND` (test projects) to put them elsewhere.

## Package

`dist/kpipe.zip` contains exactly the `kpipe/` folder, so it can be unzipped and used
without the rest of this repository.

## Notes

- The default artist name in the scene manager is `artist`; the HDA file still carries the
  author's own default in one parameter, change it in the Scene Manager.
- Old reference files and handoff notes from the source workspace are not included.
