#!/usr/bin/env python3
"""Inject a graphdata JSON payload into the 3D viewer template.

Usage:
    python3 scripts/inject_viewer_data.py viewer-template.html graphdata.json my-viewer.html

The graphdata contract is documented in the header comment of
viewer-template.html and in .claude/skills/build-curriculum-taxonomy/SKILL.md.
"""
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit("usage: inject_viewer_data.py <template.html> <graphdata.json> <out.html>")

tpl, data, out = (Path(p) for p in sys.argv[1:4])
html = tpl.read_text(encoding="utf-8")
marker = '<script id="graphdata" type="application/json">__DATA__</script>'
if html.count(marker) != 1:
    sys.exit("template is missing the graphdata marker (or has more than one)")

# "</" would terminate the inline <script> block early, so escape it
payload = data.read_text(encoding="utf-8").replace("</", "<\\/")
out.write_text(html.replace(marker, marker.replace("__DATA__", payload), 1), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
