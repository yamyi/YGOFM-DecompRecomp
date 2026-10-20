# media/video — raw notes

Session: 2026-09-04.

## The chunk contains a complete MDEC encoder

`site/js/extend/tools/media/video.0b7c9dee.js`, 25,891 bytes. No `ffmpeg`, no `wasm`, no upload —
grep for `wasm|ffmpeg|api/v2/.*video` finds nothing. What it does contain:

| symbol | what it is |
|---|---|
| `_(t)` | clamp 0..255 |
| `O(video, t)` | promise around `seeked` |
| `S(rgba, w, h)` | RGB -> Y plane + 2x2-subsampled interleaved `[Cr, Cb]` plane |
| `k`/`T` | grab loop: `<video>` -> canvas, letterbox, `min(duration, maxDuration)*fps` frames |
| `D` | 64-entry quant matrix (`2,16,19,22,26,27,29,34, 16,16,22,...`) |
| `E` | 64-entry zigzag |
| `N` | 8x8 fixed-point DCT cosine matrix (23170, 32138, 30273, 27245, 18204, 12539, 6392) |
| `B` | 111-row AC VLC table `[bits, code, run, level]` |
| `V`/`W`/`q` | build the (run,level) -> (bits,value) map; escape = 22 bits `0x10000 \| run<<10 \| level&1023` |
| `z(block)` | in-place integer forward DCT |
| `H` | bit writer: 16 bits MSB-first per word, flushed low byte then high byte |
| `X`/`K`/`Q` | int16 wrap / round-half-away / clamp to [-512, 510] |
| `Y(y, c, w, h)` | macroblock extractor, column-major, `[Cr, Cb, Y00, Y01, Y10, Y11]` |
| `Z(bw, block, qtab)` | encode one block: 10-bit DC, AC codes, EOB `10` |
| `ee(mbs, budget)` | try quant scale 1..63, keep the first that fits |
| `te({...})` | STR muxer |

Component props (the only knobs, none exposed in the UI):

    width 320  height 240  fps 15  cdSpeed 2  maxDuration 22
    downloadName "MOVIE.STR"   (hard-coded; the computed basename is discarded)
    DragAndDrop accepted-types ".mp4"   (suffix match on the filename only)

Header text: `Trailer Encoder / PSX STR · MDEC BS v2`, chips `320×240`, `15 fps`, `×2 CD`, `mín 22s`,
and *"The video can last more than 22s but only the first 20s are considered, 2s are requested as
buffer to avoid infinite loops in the .str"*.

`ee()` output header, verbatim:

    S[0]=_&255; S[1]=_>>8;   // _ = (codes+1)>>1  after codes = (codes+2+63)&-64
    S[2]=0; S[3]=56;         // 0x3800
    S[4]=a&255; S[5]=a>>8;   // quant scale
    S[6]=2; S[7]=0;          // version 2

`te()` sector header, verbatim:

    j[0]=96; j[1]=1;             // 0x0160
    j[2..3]=videoId (32769)
    j[4..5]=y/2016               // chunk index
    j[6..7]=b/2016               // chunk count
    j[8..11]=w                   // frame number (1-based)
    j[12..15]=_                  // bytesUsed, (bw.used+3)&-4
    j[16..17]=n  j[18..19]=r     // width, height
    j.set(C.subarray(0,8), 20)   // copy of the frame header; +28..31 stay zero
    P = Uint8Array(2048); P.set(j,0); P.set(C.subarray(y, y+2016), 32)

Rate control: `v = 75*cdSpeed*fpsDen = 150`, `m = fpsNum = 15`; per frame `g += v;
b = 2016*floor(g/m); g %= m` -> constant **10 sectors / 20160 bytes per frame**.

## Disc facts

    eo.walk_iso(disc):
      /DATA/MASTER.XA   lba=199930  size=  5742592
      /DATA/MODEL.MRG   lba= 28534  size=351019008
      /DATA/MOVIE.STR   lba=202734  size= 35430400   <-- 17300 sectors
      /DATA/SD_BGM.DAT  lba=  2936  size= 14675968
      /DATA/SD_SE.DAT   lba=  2193  size=  1521664
      /DATA/SU.MRG      lba=   954  size=  2537472
      /DATA/WA_MRG.MRG  lba= 10102  size= 37748736
      /SLUS_014.11      lba=    24  size=  1902592
      /SYSTEM.CNF       lba=    23  size=       68

Raw scan of 17300 sectors from LBA 202734:

    subheader(file,chan,submode,coding) counts:
      00014800 : 15139   video, Form1, submode 0x48 = Data|RT
      0001C800 :     1   the very last sector, EOF flag set
      01016401 :  2160   XA audio, Form2, submode 0x64 = Audio|Form2|RT, coding 0x01
    dims {(320,240)}   chunk-count field {8, 9}   quant scale 1..9   version 2
    distinct frame numbers 1..346, each seen 5 times
    frame-number restarts at sectors 3460, 6920, 10380, 13840

Copy comparison (user data of each 3460-sector block):

    0 0622060bb7cdca71014f0dd8175bb387164a46e6
    1 0622060bb7cdca71014f0dd8175bb387164a46e6
    2 0622060bb7cdca71014f0dd8175bb387164a46e6
    3 0622060bb7cdca71014f0dd8175bb387164a46e6
    4 261c90f61df8482910d6a50cb9f5d844c7fea05d   <- differs in ONE sector (index 3459):
                                                    subheader 00014800 -> 0001C800

Per-copy census: 260 frames with `cc=9` and 86 with `cc=8`; actual video sector counts match `cc`
exactly (so the +6 field is a **count**, not a last-index). 260*9 + 86*8 = 3028 video + 432 audio
= 3460 sectors, 346 frames.

XA audio sample: sector 202741, subheader `01 01 64 01`, coding byte `0x01` -> stereo, 37.8 kHz,
4-bit ADPCM, payload non-zero.

## Game side

Filename table, SLUS file 0x80F00..0x80F8B (RAM 0x80090700..0x8009078B), pointer array at file
0x80F8C (RAM 0x8009078C) -> 7 entries in this order:

    \DATA\WA_MRG.MRG;1  \DATA\SU.MRG;1  \DATA\MODEL.MRG;1  \DATA\MOVIE.STR;1
    \DATA\SD_SE.DAT;1   \DATA\SD_BGM.DAT;1  \DATA\MASTER.XA;1

`gFile_anLba = 0x800E9EA8` (16-entry word table, per `src/func_80013940.c`), so
`D_800E9EB4 = gFile_anLba[3] = MOVIE.STR's LBA`. Zero in the file image; filled at runtime.

Stream table:

    $ xxd -s 0x81D1C -l 16 SLUS_014.11
    00081d1c: 080c 2f01 0000 0000 0000 0000 0000 0000

    D_8009151C[0] = { u16 f0 = 0x0C08 = 3080 sectors, u16 f2 = 0x012F = 303 frames }
    (asm/asm_803E0.s:  alabel D_8009151C  /* 81D1C 8009151C 080C2F01 */)

Everything after entry 0 is zero. 303 frames / 15 fps = 20.2 s; the file holds 346 = 23.07 s.
3080 sectors < 3460, so the game reads only part of copy 0 — copies 1..4 are never touched by this
code path.

Call chain: `func_8003594C` (0x8003594C) -> `lookup_speed_and_start_read` (0x8005C388) ->
`func_8005B8A0` (0x8005B8A0) -> `str_stream_wait_and_decode_frame`.

`func_8005B8A0` body highlights (from `src/func_8005B8A0.c`):

    DecDCTReset(0);
    DecDCToutCallback(0x80060000 - 0x3E0C);      // = 0x8005C1F4
    DecDCTvlcBuild((void*)D_8009B498);
    StSetRing((void*)(D_8009B498 + 0x11000), 0x14);
    StClearRing();
    StSetStream(D_8009B060, D_8009B068, D_8009B06C, 0, 0x80060000 - 0x3970);  // = 0x8005C690
    if (D_8009B06C >= 5) D_8009B06C -= 4;
    str_stream_wait_and_decode_frame(0);

## Script work

`str_tool.py` already had `info`/`check`/`decode`/`extract` from the previous session. Two changes:

1. **Bug fix.** `parse_header` returned `chunks = cc + 1`. Verified against the disc that the +6
   field equals the number of video sectors the frame actually occupies, so it is a plain count.
2. **Added `encode`** — a full port of the chunk's `S/Y/z/H/Z/ee/te`, so the folder now clones the
   tool's actual capability rather than only reading its output.

Validation of the encoder:

    # synthetic gradients, deliberately high-frequency
    str_tool.py encode encsrc --out test.str --seconds 0.3
      -> 40 sectors for 4 frames (10/frame), quant scale 5, PSNR ~20.5 dB (pathological source)

    # the game's own frames, decoded then re-encoded
    str_tool.py decode MOVIE.STR --out frames --count 3 --skip 100
    str_tool.py encode frames --out real.str --seconds 1
    str_tool.py decode real.str --out dec2 --count 3
      -> quant scale 1..1 (same as the disc), PSNR 50.7 / 50.7 / 51.0 dB

That the encoder picks quant scale 1 on real content and round-trips at ~51 dB through an
independently written decoder is the correctness argument; the two halves share only the constant
tables, not the code paths.

## Caveats and open items

* `str_tool.py extract` (and any ISO tool) writes 2048 bytes per sector, which truncates the Form2
  XA sectors' 2324-byte payload. The flat `.STR` is fine for video work and useless for audio.
* Nothing here can rebuild the disc: putting a new MOVIE.STR back needs Mode2 subheaders + EDC/ECC,
  i.e. mkpsxiso or equivalent.
* Why five copies is still unexplained — nothing but `gFile_anLba[3]` + `D_8009151C[0]` references
  the file in the EXE.
* `StSetStream`'s first argument comes from `D_8009B060`, currently named `clearDisplay` in the
  decomp; the audio channel/file selection was not traced.
