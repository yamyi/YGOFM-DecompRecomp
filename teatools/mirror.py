#!/usr/bin/env python3
"""Mirror TEA-Online tool pages into ~/teatools/<folder>/site.  usage: mirror.py route [route...]
Folder = route minus 'extend/' and 'tools/' prefixes, '/' -> '-'.  Prints one status line per route."""
import os, re, subprocess, sys, pathlib
BASE = "https://www.basededatostea.xyz"
ROOT = pathlib.Path.home() / "teatools"
COOKIE = os.environ.get("TEA_COOKIE")   # value of the site's `ts` cookie, for login-gated routes
def curl(url, out):
    cmd = ["curl", "-sSL", "-o", str(out), "-w", "%{http_code}"] + (["-b", f"ts={COOKIE}"] if COOKIE else []) + [url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()
def folder_for(route):
    r = re.sub(r"^/?extend/", "", route.strip("/")); r = re.sub(r"^tools/", "", r)
    return r.replace("/", "-")
for route in sys.argv[1:]:
    route = route.replace(BASE, "").strip("/")
    site = ROOT / folder_for(route) / "site"; site.mkdir(parents=True, exist_ok=True)
    code = curl(f"{BASE}/{route}", site / "page.html")
    html = (site / "page.html").read_text(errors="replace")
    if code != "200" or "<div id=app>" not in html:
        print(f"{code:>4} {route} -> {site.parent.name}  (NOT a tool page)"); continue
    assets = sorted(set(re.findall(r'(?:href|src)=(/[^ >"]+\.(?:js|css|json))', html)))
    got, missing = 0, []
    def fetch(p):
        global got
        out = site / p.lstrip("/"); out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists(): got += 1; return
        c = curl(BASE + p, out)
        if c == "200": got += 1
        else: missing.append(f"{p}({c})"); out.unlink(missing_ok=True)
    for p in assets: fetch(p)
    # lazy chunks named inside the tool's own chunk(s)
    tool_js = list(site.glob("js/extend/**/*.js"))
    for js in tool_js:
        txt = js.read_text(errors="replace")
        m = re.search(r'\{("chunk-[0-9a-f]{8}":"[0-9a-f]{8}"(?:,"chunk-[0-9a-f]{8}":"[0-9a-f]{8}")*)\}', txt)
        if m:
            for name, h in re.findall(r'"(chunk-[0-9a-f]{8})":"([0-9a-f]{8})"', m.group(1)): fetch(f"/js/{name}.{h}.js")
    # data files referenced by the tool code (templates, json, bin)
    for js in tool_js:
        for p in set(re.findall(r'"(/Assets/files/[^"]+|/Assets/[^"]+\.(?:json|bin|txt|xlsx|zip))"', js.read_text(errors="replace"))): fetch(p)
    (site / "assets.txt").write_text("\n".join(assets) + "\n")
    names = ", ".join(j.name for j in tool_js) or "NO TOOL CHUNK"
    print(f"{code:>4} {route} -> {site.parent.name}  files {got}{'  MISSING ' + ' '.join(missing) if missing else ''}  [{names}]")
