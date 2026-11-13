"""Run Python inside the live Houdini session through the fxhoudinimcp hwebserver endpoint.

    python hou_exec.py [--port 8100] [--timeout 120] (-c "code" | script.py | --health)

The code runs on Houdini's main thread (hou available). Prints the JSON result.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request


def call(fn, kwargs, port=8100, timeout=120):
    body = "json=" + urllib.parse.quote(json.dumps(["mcp." + fn, [], kwargs]))
    req = urllib.request.Request("http://127.0.0.1:{}/api".format(port), data=body.encode("utf-8"),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "null")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?")
    ap.add_argument("-c", "--code")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--health", action="store_true")
    a = ap.parse_args(argv)
    if a.health:
        res = call("health", {}, a.port, a.timeout)
    else:
        code = a.code if a.code is not None else open(a.script, encoding="utf-8").read()
        res = call("execute", {"command": "code.execute_python", "params": {"code": code},
                               "request_id": "hou_exec"}, a.port, a.timeout)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False)[:8000])
    return 0 if res and res.get("status") in ("ok", "success") else 1


if __name__ == "__main__":
    sys.exit(main())
