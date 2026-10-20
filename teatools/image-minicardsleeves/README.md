# Mini Card Sleeves tool (56x64 hand/field cards, 12x16 micro cards)

Route: `extend/tools/image/minicardsleeves` (page version V.260629). Input: **WA_MRG.MRG**
(`.mrg`, 36,700,160..39,845,888 bytes) and images (`image/*`, up to 20 MB). Client-side
only (analytics POST `api/v2/tools` tipo 31). Purpose: replace the small card sprites the
duel and the library use: a 168x64 strip of three 56x64 "mini" card faces (dynamic +
static layers), the 56x64 mini card back, a 128x48 text strip, and two 12x16 "micro"
cards, with seven colour palettes. Status: decoded, disc-verified; the mini part is
sound, the micro part of the site tool is broken (see section 4); offline clone written.

Script: `scripts/mini_sleeves.py` (dump / apply / restore on a WA_MRG copy).
Templates: `site/Assets/img/templates/minicard.zip` (dynamic/static 168x64, sleeve 56x64,
text 128x48 templates + vanilla and custom examples). Raw notes: `NOTES-raw.md`.

The mini cards live inside the same card texture column as the big card; read
`../image-cardsleeves/README.md` section 1 and 3 first for the ten bundle copies, the
128-byte-row column format, the CLUT block and the loader.

## 1. Mini cards: rows 592..768 of the card texture, 8 copies

The tool's `body_offset` 0xB75800 = `0xB63000 + 592*128`, i.e. row 592 of the texture
block, and its cycles are the first eight of the card-sleeve list: the 7 arena bundles
(`0xB63000 + 0x75800*k`, sectors 5830+235k) and the library bundle (`0xEE6800`, sector 7629).
The password and 0x2189 bundles do not carry mini cards (stock rows 592..1024 differ there).

| tool name | texture rows | bytes | canvas | VRAM page (896,256) texels (8bpp) |
|---|---|---|---|---|
| text (`cardTransform3`, 128x48, index 3) | 592..640 | 0..128 | 128x48 | u0..127 v80..127 |
| tile A | 640..704 | 0..56 | canvas x 0..55 | u0..55 v128..191 |
| tile B | 704..768 | 0..56 | canvas x 56..111 | u0..55 v192..255 |
| tile C | 704..768 | 56..112 | canvas x 112..167 | u56..111 v192..255 |
| tile D = mini sleeve (`cardTransform2`, index 2) | 640..704 | 56..112 | 56x64 | u56..111 v128..191 |

Dynamic (index 0) and static (index 1) are the 168x64 strip = tiles A,B,C
(`cardTransform1`); the display map `cardBg1` shows A,B,C,D as 224x64. In the stock file
A is a blank frame (art window empty), B and C are two frame variants with the spiral art
placeholder and an ATK/DEF bar, D is the mini card back (56x64 spiral).

Palette layout, per CLUT-block row (block row `1+k` = VRAM y `241+k` for colour k = 0..5;
colour 6 is stored in block row 1 at colour index +128):

    64..79   dynamic     80..95  static (overlay, opaque pixels only)
    96..111  sleeve (D)  112..127 text

`palleteConfig1` = `0xB83200 + 512*k + 128` (16 colours from index 64) or `0xB83380`
(k = 6: row 1, colours 192..207). The ImagePanel shows colour 6 through `0xB83200 + 256`,
i.e. pixel index i -> row-1 colour 128+i. "Generate Color 7" (`generateColor7Mini`) copies
bytes 0..255 of row 1 to +256 in all 8 copies, i.e. clones palette 0 into the 7th slot.
`salvarEnImagen` writes the layer palette to block rows 1..6 and to row 1 +256, then the
pixel indices through `cardTransform1` (always -- see the bug list) for every cycle.
Palette encoding and quantisation are the same as in the big-card tool.

Stock: colour 64 is 0 (transparent) and colour 65 is `81F8 8180 B851 CCA0 D8EB 8138 5AD6`
in block rows 1..7 respectively -- all seven rows are present and identical in the eight
copies (md5 of the 7 rows: `f0cf2a23`).

## 2. Micro cards: 12x16 4bpp tiles in the arena bundles

The tool's micro `body_offset` is 0xBC5800 = `0xB63000 + 197*2048`: bundle sector 197 of
the arena bundle, which stage 10 of the duel loader streams to VRAM **(832,0)** (8 sectors,
rows 0..127). Sector 197 is rows 112..127 of that page. The two tiles are bytes 48..53 and
54..59 of those rows: at 4bpp that is page (832,0) u 96..107 / u 108..119, v 112..127.
Only the seven arena bundles have this region; the library cycle (3684352) would put
"sector 197" at WA_MRG sector 7826, which is inside the free-duel bundle (7816..7902), and
the stock bytes there are unrelated.

Their palettes are 16-colour CLUTs in the **boot block**: `func_80043960` (called from
`Main_Init`) loads sectors 0x1690..0x16C6 (5776..5829, LBA 15878..) with callback
`func_80043328`: 48 sectors -> VRAM (640,0) 3 pages, 2 sectors -> `LoadImage2((512,248,256,8))`,
1 sector -> `LoadImage2((640,232,16,8))`, 3 sectors -> `*(0x800101D8)`. The 8-row CLUT block
is sectors 5824..5825, so WA_MRG `0xB60840` (the tool's micro `header_offset_base`
11929792) is CLUT-block byte 0x840 = row 4, colour 32: seven 16-colour palettes at
VRAM `(544 + 16*k, 252)`, k = 0..6. Stock: `0000 801F 8011 800C 8007 8018 801A 801D 83E0 ...`
(the first one is a red/orange ramp). The stock micro tiles are two fully opaque 12x16
card icons using 7 indices (`mini_sleeves.py dump` -> `micro_a.png` / `micro_b.png`).
Caveat: that 0xB60840 is the micro palette is the tool's claim (`header_offset_base`) plus
the fact that the stock bytes there are seven 16-colour palettes; which CLUT the duel really
binds to these tiles was not confirmed in-game.

## 3. What the game does with it

Same loader as the big card (`func_80014E1C` -> `D_800E9E60` -> `func_80013C28` streaming
64x16 rects, page-column order). Mini cards are drawn by the duel overlay and the library
from page (896,256) with a CLUT id for row 241+k; nothing about them is resident in RAM.
Which sprite uses tile A/B/C where (hand, field face-down, library list) was not traced;
the tool's INFO tab only says "card image and card sleeve image".

## 4. Bugs in the site tool (as mirrored, V.260629)

* The micro images (indexes 4..6) are written with `setNewBody` using `this.cardTransform1`
  (the three 56x64 mini chunks) and a 12-pixel-wide body, as 8bpp bytes: the body lookup runs
  off the end of the 192-entry index array and throws, and no 4bpp packing is done. Micro
  tiles cannot actually be replaced with the tool.
* The micro palette write goes to `0xB60840 + cycle` for all 8 cycles: only cycle 0 is the
  boot CLUT; cycles 1..6 land in the previous arena bundle's stage-12 pixel data (sector 230,
  VRAM (704,256) rows 432..447) and cycle 7 in the free-duel bundle. The ImagePanel and the
  palette editor instead read `0xF20BC0 + 32*k` (library bundle sector 116, which stage 4
  of the library loader uploads as CLUT rows 246/247 -> VRAM (480,247)), a region that is
  all zero on the stock disc. "Generate Color 7" for micro copies 32 bytes at that offset to
  +192. `mini_sleeves.py` ignores all of this and edits the real locations (tiles in the 7
  arena bundles, palettes at 0xB60840).
* The page still contains the big-card POSITION code (SLUS reader is hidden, `dataviewSlus`
  is never set), so nothing is written to SLUS_014.11.

## 5. Recomp options

1. **VRAM-level replacement** (same hook as the big card): when the CLUT rect
   `(256,240,256,16)` is uploaded, page (896,256) rows 80..255 are complete: upload the mod's
   mini strip, back and text (quantised to 16 colours each) to (896, 336..511) and write CLUT
   rows 241..246 (+ row 241 colours 192..255 for the 7th) at indices 64..127.
2. Micro tiles: after the boot block (once, at start-up: `func_80043960` returns before the
   first frame) write the 16-colour CLUTs at (544+16k, 252), and after each arena load write
   12x16 4bpp tiles at (832+48/2.., 112..127) -- i.e. rect (856, 112, 6, 16) halfwords.
3. Disc-level substitution of sectors 5830+235k+ (37..48) and 197, as for the big card.

## 6. Decomp findings (proposed)

* WA_MRG `0xB75800 (+0x75800k)`, `0xEF9000` | 176 rows of the card texture (592..768): 128x48 text strip and four 56x64 mini cards -> VRAM page (896,256) v80..255; palettes CLUT rows 241..246 indices 64..127 | (facts)
* `0x80043960` | boot-time request of the common UI block: `(0x1F85, 0x22, func_800434F4)` then `(0x1690, 0x36, func_80043328)`; the second lands 3 pages at (640,0),(704,0),(768,0), an 8-row CLUT block at (512,248) and a 16x8 rect at (640,232) | `Main_RequestBootGraphics`
* WA_MRG `0xBC5800 (+0x75800k)` | arena bundle sector 197 -> VRAM (832,0) rows 112..127: two 12x16 4bpp micro card tiles at u96/u108; CLUTs (544+16k,252) from WA_MRG 0xB60840 | (facts)

## 7. Open questions

* Which duel/library sprites use which mini tile, and where the micro tiles are drawn.
* What TEA's own WA_MRG puts at 0xF20BC0 (the tool reads micro palettes from there; stock
  is zero), i.e. whether V.260629 targets a modified layout.
* Row 7 of the CLUT block (VRAM y 247) holds a 7th mini palette in stock but the tool
  never writes it; and the library loader overwrites rows 246/247 with bundle sector 116.
