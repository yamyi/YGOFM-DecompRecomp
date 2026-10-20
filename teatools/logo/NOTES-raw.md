# logo — raw working notes

## Mirror

`site/js/extend/tools/logo.2201f92e.js`, pretty-printed with
`sed 's/},{/},\n{/g; s/;/;\n/g'`. Relevant identifiers:

* `Je` — the 6 foreground chunks (`{width,height,data:{ci,cf},canvas:{ci,cf}}`).
* `Ke` — the single background chunk (256x256 from 128x256 bytes, `ppb: 2`).
* `Xe` — the two file layouts (`Main image` / `Prologue image`) with `offset.front.body`,
  `offset.front.pallete`, `offset.back.body`, `offset.back.pallete`, `size.min/max`, `filename`,
  and the `fix[]` array of `{address, data[46]}`.
* `Qe` — `LogoEditor`: `salvarEnImagen` -> `setNewHeader` + `setNewBody`;
  `salvarEnImagenBG` -> `setNewHeaderBG` + `setNewBodyBG`; `makeTrasparent`; `addCode` writes the
  `fix` records; `download` does `saveAs(new Blob([dataview.buffer]), filename)`.
* `_e` (`ImagePatched`) — the previewer. `paintCanvas` reads
  `body_offset + bytes_width*ci.y + bytes_width*floor(i/(w/ppb)) + i%(w/ppb) + ci.x`;
  `getHeader` decodes BGR555 as `r=(b0&0x1F)<<3`, `g=((b1&3)<<6)|((b0&0xE0)>>2)`,
  `b=(b1&0x7C)<<1`, `a = (b0|b1)==0 ? 0 : 255`.
* `Me` (`ImageConverter`) — `createHeader` / `createBody`, shared with the icon and font tools.
* `We` (`FileSystemTree`) — the fake disc tree; `SU.MRG` accepts `.mrg`, `maxsize 44040192`.

Decimal constants seen in the chunk and what they are:

    197120 = 0x30200   198656 = 0x30800   234042 = 0x3923A
 16594944 = 0xFD3800 16693248 = 0xFEB800 16693760 = 0xFEBA00
 16593198 = 0xFD312E 16695594 = 0xFEC12A

(An earlier pass of these notes had `0x30400`, `0xFD30AE` and `0xFEC1AA` — all three were arithmetic
slips. `0x30400` renders a grey ramp, not the logo; the corrected `0x30200` renders the real thing
and matches the WA copy bit-for-bit except STP.)

## Disc extraction used for verification

```python
import sys, mmap; sys.path.insert(0, '/home/codyj/ygofm-decomp/tools')
import extract_overlay as eo
f = open('.../Yu-Gi-Oh! Forbidden Memories (USA).bin', 'rb')
disc = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
list(eo.walk_iso(disc))
# /DATA/SU.MRG      lba 954    size 2537472
# /DATA/WA_MRG.MRG  lba 10102  size 37748736
```

md5 of the extracted files: `ad9862e1e289bbb7cfb4f1fa09de7f93` (SU.MRG),
`971c16ea21635b45351e5ae959c53503` (WA_MRG.MRG).

## Verified byte facts

* SU `0x3923A`, WA `0xFD312E`, WA `0xFEC12A` all hold the same stock 46 bytes
  `07 10 00 00 00 80 00 02 e0 09 00 18 18 43 e0 06 00 88 98 43 e0 06 00 38 d0 42 c0 12 80 80 a0 02
  e0 09 80 00 10 00 e0 1f 00 00 00 00 e0 1f`.
* SU/WA background pixels identical; background CLUTs identical.
* SU/WA foreground CLUTs differ in 255 of 512 bytes, always only bit 15 (SU sets STP, WA does not).
* SU/WA foreground pixels differ in 3,099 bytes, all inside file rows 208..239 (the copyright line).
* The two WA descriptor blobs `0xFD3000` and `0xFEC000` differ in bytes `0x000..0x187` (their header
  tables and first streams) and are identical from `0x188` to the end of the sector.

## How the two-strip layout was proven

Decode the stock 7 quads with `u=(A&0x1F)*8`, `v=((A>>5)&0x1F)*8`, `w=((B>>5)&0xF)*8+8`,
`h=((B>>9)&0xF)*8+8`, `x=b0|((A>>14)&3)<<8`, `y=b1|((B>>14)&3)<<8` and compare against the site's
own 6-chunk table. The chunks that need `u >= 128` are exactly the ones whose data row in the site's
128x512 model is 256 higher than `v`:

    quad uv(128,  0) 128x128  <-> chunk data (  0,256)   +256
    quad uv(192,168)  64x56   <-> chunk data ( 64,424)   +256
    quad uv(192,224)  64x32   <-> chunk data ( 64,480)   +256
    quad uv(128,176)  64x80   <-> chunk data (  0,432)   +256
    quad uv(  0,  0) 128x128  <-> chunk data (  0,  0)
    quad uv(  0,128) 128x40   <-> chunk data (  0,128)
    quad uv(  0,168) 128x40   <-> chunk data (  0,168)

i.e. `file = 0x8000*(u>=128) + 128*v + (u&127)`. The decomp's loader then explains why: the CD pump
uploads one 0x8000-byte column (64 halfwords x 256 rows) at a time.

## Rendering sanity check

`logo_image.py dump SU.MRG t` produces the correct "Yu-Gi-Oh! FORBIDDEN MEMORIES" logo at 320x168
and the hieroglyph wallpaper at 256x256. The 128x512 raw view additionally shows
"© 1996 KAZUKI TAKAHASHI" (rows 208..239) and "PUSH START BUTTON" (rows 384..431 = texture x
128..255, y 128..175), neither of which is inside the tool's canvas.

Rendering WA `0xFC2800` (the *other* boot picture, whose descriptor blob the tool also patches) with
CLUT `0xFD2800` gives the Konami / Shueisha / "原作 高橋和希 週刊少年ジャンプ" legal screen — so the
`0xFD312E` fix is applied to a group belonging to a different picture.

## Script tests (scratch copies only)

    logo_image.py check SU.MRG            -> "STOCK", 255/256 CLUT entries with STP
    logo_image.py dump  su_test.mrg t1
    logo_image.py import su_test.mrg -o su_mod.mrg --front t1_front.png --back t1_back.png
    logo_image.py dump  su_mod.mrg t2     -> t1 vs t2: max channel delta 0, 0 pixels differ
    logo_image.py restore su_mod.mrg SU.MRG -o su_res.mrg ; cmp su_res.mrg SU.MRG  -> identical

Same for WA_MRG.MRG (both fix addresses report FIXED after import; restore byte-exact).
