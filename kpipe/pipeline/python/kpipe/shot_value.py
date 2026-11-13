"""Shot Value SOP (kpipe::shot_value::1.0): a value that changes per shot.

No inputs. Outputs empty geometry with one detail attribute (name = Attribute) holding the
result, and shows the result on the Result parm so it can be copied / referenced.

    Match          string to match, by default `chs("/obj/scene_manager/var_shot")`;
                   any parm reference or literal works
    Default Value  used when no rule matches
    Rules          multiparm, top to bottom, first enabled match wins:
                   Pattern (space separated, * wildcards, e.g. "GRS_0010 GRS_00*") -> Value
                   (reorder with the multiparm's own controls)

Type (Float / Int / String / Vector) picks which Default / Value / Result parms are used.
"""

import fnmatch
import os

import hou

from . import config, scene

_PY = hou.scriptLanguage.Python
TYPES = ("float", "int", "string", "vector")
_KIND = {"float": "f", "int": "i", "string": "s", "vector": "v"}
_RESULT_EXPR = '__import__("kpipe.shot_value").shot_value.result(hou.pwd(), "{kind}"){comp}'
_COOK = "import kpipe.shot_value\nkpipe.shot_value.cook(hou.pwd())\n"
_TOOL = """<?xml version="1.0" encoding="UTF-8"?>
<shelfDocument>
  <tool name="$HDA_DEFAULT_TOOL" label="$HDA_LABEL" icon="$HDA_ICON">
    <toolMenuContext name="viewer">
      <contextNetType>SOP</contextNetType>
    </toolMenuContext>
    <toolMenuContext name="network">
      <contextOpType>$HDA_TABLE_AND_NAME</contextOpType>
    </toolMenuContext>
    <toolSubmenu>KPipe</toolSubmenu>
    <script scriptType="python"><![CDATA[import soptoolutils
soptoolutils.genericTool(kwargs, '$HDA_NAME')]]></script>
  </tool>
</shelfDocument>
"""


# ---------------------------------------------------------------- evaluation

def _kind(n):
    return _KIND[n.parm("type").evalAsString()]


def _value(n, base, kind):
    if kind == "v":
        return tuple(n.parmTuple(base).eval())
    return n.evalParm(base)


def matches(pattern, key):
    """True when key matches any space separated pattern (* and ? wildcards)."""
    return any(fnmatch.fnmatchcase(key, p) for p in pattern.split())


def matched_rule(n):
    """1-based index of the rule in use, or 0 for Default Value."""
    key = n.evalParm("match").strip()
    for i in range(1, n.evalParm("rules") + 1):
        if n.evalParm("enable{}".format(i)) and matches(n.evalParm("pattern{}".format(i)), key):
            return i
    return 0


def result(n, kind=None):
    """Value for node n: the first enabled rule whose Pattern matches Match, else Default.

    kind: f / i / s / v, defaults to the Type parm.
    """
    kind = kind or _kind(n)
    i = matched_rule(n)
    return _value(n, "value_{}{}".format(kind, i) if i else "default_" + kind, kind)


def cook(sop):
    """Python SOP body inside the HDA: write the result as a detail attribute."""
    n = sop.parent()
    name = n.evalParm("attrib").strip()
    if not name:
        raise hou.NodeError("Set Attribute (the detail attribute name)")
    value = result(n)
    geo = sop.geometry()
    geo.clear()
    default = {"f": 0.0, "i": 0, "s": "", "v": (0.0, 0.0, 0.0)}[_kind(n)]
    geo.addAttrib(hou.attribType.Global, name, default)
    geo.setGlobalAttribValue(name, value)


# ---------------------------------------------------------------- HDA

def _typed(prefix, label, help_text, expr=None, suffix=""):
    """Float / Int / String / Vector variants of one parm, shown by Type, each on a short row."""
    out = []
    for token, cls, size in (("float", hou.FloatParmTemplate, 1), ("int", hou.IntParmTemplate, 1),
                             ("string", hou.StringParmTemplate, 1), ("vector", hou.FloatParmTemplate, 3)):
        name = prefix + _KIND[token]
        kwargs = {}
        if expr is not None:
            exprs = [expr.format(kind=_KIND[token], comp="" if size == 1 else "[{}]".format(c))
                     for c in range(size)]
            kwargs = {"default_expression": exprs, "default_expression_language": [_PY] * size}
        pt = cls(name + suffix, label, size, **kwargs)
        hide = "{ type != %s }" % token
        pt.setConditional(hou.parmCondType.HideWhen, hide)
        pt.setHelp(help_text)
        out += scene.row(name + suffix, pt, hide_when=hide)
    return out


def _templates():
    out = []
    attrib = hou.StringParmTemplate("attrib", "Attribute", 1, default_value=("value",))
    attrib.setHelp("Name of the detail attribute written on the output geometry.")
    out += scene.row("attrib", attrib)
    kind = hou.MenuParmTemplate("type", "Type", TYPES, ("Float", "Int", "String", "Vector"))
    kind.setHelp("Value type of Default Value, the rule Values, Result and the attribute.")
    out += scene.row("type", kind)
    match = hou.StringParmTemplate("match", "Match", 1,
                                   default_value=('`chs("{}/var_shot")`'.format(config.SM_PATH),))
    match.setHelp("String the rule Patterns are matched against. Default: the Scene Manager's"
                  " effective shot (follows TOP work items). Any parm reference or literal works.")
    out.append(match)
    out += _typed("default_", "Default Value", "Value used when no rule matches.")
    out += _typed("result_", "Result", "Current value (live). Copy this parm to reference it elsewhere.",
                  expr=_RESULT_EXPR)
    out.append(hou.SeparatorParmTemplate("sep_rules"))

    rules = hou.FolderParmTemplate("rules", "Rules", folder_type=hou.folderType.MultiparmBlock,
                                   default_value=0)
    rules.setHelp("Checked top to bottom; the first enabled rule whose Pattern matches wins.")
    enable = hou.ToggleParmTemplate("enable#", "Enable", default_value=True)
    enable.setHelp("Use this rule.")
    pattern = hou.StringParmTemplate("pattern#", "Pattern", 1, default_value=("",))
    pattern.setHelp("Space separated values to match, * and ? wildcards, e.g. GRS_0010 GRS_00*.")
    for pt in scene.row("pattern#", enable, pattern) + _typed("value_", "Value", "Value when this rule matches.",
                                                               suffix="#"):
        rules.addParmTemplate(pt)
    out.append(rules)
    return out


def build_hda(path=config.SV_HDA):
    """(Re)generate the Shot Value SOP HDA file.

    When it is already installed from `path`, the definition is updated in place (interface
    and sections; the inner Python SOP is kept), so existing nodes keep their values.
    """
    cat = hou.sopNodeTypeCategory()
    d = scene.installed_definition(cat, config.SV_TYPE, path)
    saved = []
    if d is None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        saved = scene.save_instances(cat, config.SV_TYPE)
        if os.path.exists(path):
            hou.hda.uninstallFile(path)
            os.remove(path)
        geo = hou.node("/obj").createNode("geo", "kpipe_sv_build")
        sub = geo.createNode("subnet", "shot_value")
        py = sub.createNode("python", "write_value")
        py.parm("python").set(_COOK)
        out = sub.createNode("output", "output0")
        out.setInput(0, py)
        out.setDisplayFlag(True)
        out.setRenderFlag(True)
        sub.layoutChildren()
        asset = sub.createDigitalAsset(name=config.SV_TYPE, hda_file_name=path,
                                       description="KPipe Shot Value",
                                       min_num_inputs=0, max_num_inputs=0)
        d = asset.type().definition()
        geo.destroy()
    d.setParmTemplateGroup(scene.interface(cat, _templates()))
    d.addSection("Tools.shelf", _TOOL)
    d.setIcon("SOP_attribcreate")
    scene._remove_backup(path)
    scene.restore_instances(saved)
    return path


def ensure_hda():
    if hou.nodeType(hou.sopNodeTypeCategory(), config.SV_TYPE):
        return
    if not os.path.exists(config.SV_HDA):
        build_hda()
    hou.hda.installFile(config.SV_HDA, change_oplibraries_file=False)


def create(parent, name="shot_value"):
    """Create a Shot Value node inside SOP network `parent` (API / MCP use)."""
    ensure_hda()
    return parent.createNode(config.SV_TYPE, name)


def _network_editor():
    pane = hou.ui.paneTabUnderCursor()
    if pane is not None and pane.type() == hou.paneTabType.NetworkEditor:
        return pane
    return hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)


def create_here():
    """Shelf tool: create a Shot Value node in the network editor's current SOP network.

    Does nothing (status message) when that network is not a SOP network.
    """
    pane = _network_editor()
    net = pane.pwd() if pane is not None else None
    if net is None or net.childTypeCategory() != hou.sopNodeTypeCategory():
        hou.ui.setStatusMessage("Shot Value: open a SOP network first", hou.severityType.Warning)
        return None
    n = create(net)
    n.setPosition(pane.cursorPosition())
    n.setSelected(True, clear_all_selected=True)
    n.setCurrent(True)
    return n
