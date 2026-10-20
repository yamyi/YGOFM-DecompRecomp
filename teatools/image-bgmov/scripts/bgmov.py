#!/usr/bin/env python3
"""BGMOV (moving / parallax cutscene background, up to 3 layers) -- thin wrapper.

Same record format and disc loader as the static and composite pictures
(text-script command F7 05 NN 02); the implementation lives in
../../image-background/scripts/cutscene_bg.py and this wrapper presets --mode mov.

  bgmov.py inspect <wa>
  bgmov.py export  <wa> <NN> <out.png> [--layer 1|2|3] [--strip]
  bgmov.py import  <wa.mrg> <NN> <in.png> <out.mrg> [--layer 1|2|3]
  bgmov.py restore <wa.mrg> <NN> --stock <stock> <out.mrg>
  bgmov.py verify  <wa> --stock <stock>

NN = game picture number 0..12 (the site's list shows NN+1).  Layer-1 size depends
on NN (512x160, 320x256, 512x256 or 344x256 -- `inspect` prints it); layers 2/3
are 320x160 and only some pictures use them.
"""
import os, runpy, sys
os.environ.setdefault("CUTSCENE_BG_MODE", "mov")
core = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "image-background", "scripts", "cutscene_bg.py")
if not os.path.exists(core): sys.exit(f"missing {core} (this wrapper needs the image-background folder next to image-bgmov)")
runpy.run_path(core, run_name="__main__")
