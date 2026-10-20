#!/usr/bin/env python3
"""Regenerate site-index/README.md status column from what exists on disk."""
import pathlib, re
root = pathlib.Path(__file__).resolve().parent
p = root/'site-index'/'README.md'
out, done = [], 0
for line in p.read_text().splitlines():
    m = re.match(r'\| (\S+) \| (\S+)/ \| (.+) \|$', line)
    if m:
        folder = m.group(2)
        has = (root/folder/'README.md').exists()
        scripts = list((root/folder/'scripts').glob('*.py')) if (root/folder/'scripts').is_dir() else []
        st = ('done' + (f' +{len(scripts)} script' + ('s' if len(scripts) > 1 else '') if scripts else '')) if has else 'agent'
        done += has
        line = f"| {m.group(1)} | {folder}/ | {st} |"
    out.append(line)
p.write_text("\n".join(out) + "\n")
print(f"{done}/45 tools documented")
