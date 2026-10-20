# BGCOMP tool (composite cutscene pictures: backdrop + character + light)

Route: `extend/tools/image/bgcomp` (V.220316). Input: WA_MRG.MRG (`.mrg`,
37,748,736..39,845,888 bytes) plus up to three PNG/BMP images of 320x160 (layers 1 and 2:
256 colours, layer 3: 16 colours). Client-side; WA_MRG.MRG is downloaded back.
Script: `scripts/bgcomp.py` (wrapper over `../../image-background/scripts/cutscene_bg.py`
with `--mode comp`). Raw notes: `../image-background/NOTES-raw.md`.
Status: decoded, disc-verified, PNG round trip of all three layers and byte-identical restore
tested on a copy, not yet built as a mod.

These are the cutscene pictures that carry a character over the backdrop: layer 1 is the
scene, layer 2 a keyed sprite sheet (e.g. Simon in NN 00), layer 3 a 16-colour additive
"light" layer (a glow / halo). The site lists 42 pictures as 01..42; the game's picture number
is NN = list index - 1 (00..41), i.e. command `F7 05 NN 01`.

## 1. The record

One picture = 81 sectors (0x28800 bytes):

    WA offset  = 0x1423800 + NN * 0x28800         (NN = 0..41)
    in-file sector = 0x2847 + NN * 0x51           disc LBA = 20413 + NN * 81
    (site: body 0x1423800 + 165888*(i-1); palettes 0x144B800 / 0x144BA00 / 0x144BC00)

| in-record | size | content |
|---|---|---|
| +0x00000 | 0x10000 | layer 1 strip: 512 rows x 128 B, 8bpp |
| +0x10000 | 0x10000 | layer 2 strip: 512 rows x 128 B, 8bpp (index 0 = transparent) |
| +0x20000 | 0x08000 | layer 3 strip: 256 rows x 128 B, **4bpp** (256 px per row, low nibble first) |
| +0x28000 | 0x200 | CLUT 1 (256 entries, stock: no STP bits) |
| +0x28200 | 0x200 | CLUT 2 (256 entries; entry 0 = 0x0000 transparent, no STP) |
| +0x28400 | 0x20 | CLUT 3 (16 entries; entry 0 = 0, **all 15 others have STP set** -> semi-transparent draw) |
| +0x28420 | rest | zero |

Layers 1 and 2 use the static picture's four-chunk layout (see image-background/README.md,
layer 2 with strip rows +512). Layer 3, being 4bpp, fits differently:

| strip px x, row (w x h) | canvas x, y |
|---|---|
| 0, 1024 (256x160) | 0, 0 |
| 128, 1184 (64x80) | 256, 0 |
| 192, 1184 (64x80) | 256, 80 |

(rows counted from the record start; the 4bpp strip begins at row 1024).

## 2. What the game does with it

Same loader as the static pictures (`Script_OpShowImage` -> `func_8002DF2C` with mode 1:
stride 0x51, base 0x672 -> sector `0x2847 + NN*0x51`; callback `func_8002DDFC`). The 80 pixel
sectors stream to VRAM in 16-sector columns from (0,256): columns x = 0, 64 hold layer 1,
x = 128, 192 layer 2, x = 256 layer 3 (4bpp: 128 bytes = 64 halfwords = 256 px, one column).
The CLUT sector lands at (0,240) as a 256x4 rect: row 240 = CLUT 1, 241 = CLUT 2, 242 = CLUT 3
(first 16 halfwords). The CLUT STP evidence says layer 3 is drawn with semi-transparency
(additive glow) and layer 2 as a keyed sprite; the draw code that composes the three quads was
not traced (see open questions).

Consequences: sizes are fixed by the slot (320x160 each, 8/8/4 bpp); a picture that does not
use layer 2 or 3 still has the slot (the site tells users to upload a solid colour, i.e. the
game always draws them -- with CLUT entry 0 = transparent that is invisible).

## 3. Site details

- Layer 1 is written solid (black -> (8,8,8)); layers 2/3 get a "click a colour to make it
  transparent" step (`makeTrasparent`): the clicked colour is removed from the palette, entry 0
  becomes (0,0,0,0) and pixel indices are remapped (`o[t]=0` for the removed colour, `+1` below
  it). Clicking a transparent pixel restores the original conversion.
- `setNewHeader` sets the STP bit on every non-black colour it writes -- for layer 3 that
  matches stock; for layers 1/2 stock has none (no visible effect for opaque draws).
- `getPointer` prints the BCD byte of (index-1).

## 4. Recomp options

As for the static pictures (disc patch; `LoadImage2` source swap keyed on the picture code
in `D_800EAE98->f3C`; or a post-load VRAM upload). The rects to recognise are
`(64k, 256+16j, 64, 16)` for k = 0..4 and the CLUT rect `(0, 240, 256, 4)`.

## 5. Decomp findings (proposed)

- mode 1 of `func_8002DF2C` | composite pictures: 42 x 81 sectors from WA sector 0x2847; record layout as in section 1 (three strips, three CLUTs in one sector) | (disc fact)
- CLUT 3 | every stock composite/moving picture has STP set on all 15 colours of the 16-colour light layer and none on layers 1/2 -> the light layer is drawn semi-transparent | (rendering fact, draw site not located)

## 6. Open questions

- The draw path that composes layer 2 over layer 1 and blends layer 3 (texpage/CLUT setup
  for the three quads) was not located; `Script_OpShowImage` only allocates one 320x160 quad
  (`func_80040510(rec, 0,0, 0x140,0xA0, 0,0, 0x17, 0, 0xF4)`), so the extra layers are drawn
  elsewhere (candidates: the object created via `get_or_init_D_800EFE48_slot(.., 3)`).
- Whether any picture's layer 3 is animated (flicker) -- the site treats it as static.
