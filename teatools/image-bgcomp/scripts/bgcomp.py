#!/usr/bin/env python3
"""BGCOMP (composite cutscene background, 3 layers) -- thin wrapper.

The composite pictures are the same record format and disc loader as the static
and moving ones (text-script command F7 05 NN 01), so the implementation lives in
../../image-background/scripts/cutscene_bg.py; this wrapper just presets --mode comp.

  bgcomp.py inspect <wa>
  bgcomp.py export  <wa> <NN> <out.png> [--layer 1|2|3] [--strip]
  bgcomp.py import  <wa.mrg> <NN> <in.png> <out.mrg> [--layer 1|2|3]
  bgcomp.py restore <wa.mrg> <NN> --stock <stock> <out.mrg>
  bgcomp.py verify  <wa> --stock <stock>

NN = game picture number 0..41 (the site's list shows NN+1).
"""
import os, runpy, sys
os.environ.setdefault("CUTSCENE_BG_MODE", "comp")      # an explicit --mode still overrides
core = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "image-background", "scripts", "cutscene_bg.py")
if not os.path.exists(core): sys.exit(f"missing {core} (this wrapper needs the image-background folder next to image-bgcomp)")
runpy.run_path(core, run_name="__main__")
