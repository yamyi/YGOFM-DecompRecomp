# Game Font tool

Route: `extend/tools/image/gamefont` (Font Editor V. 20260729; the loader zone still says "Ritual Engine
Editor | V. 20251123"). Input: WA_MRG.MRG (the file input accepts `.mrg,*`; the page only warns if the size
is more than 40 MB away from ~36 MB, and refuses files shorter than 0xB48000+21504 or 0xB60800+32 bytes).
Regenerates the game's text font sheet from a system/web font (name, weight, glyph scale 50..150 %, vertical
offset -6..+6 px), lets you edit the two character grids, previews the result, and downloads
`WA_MRG_modificado.MRG` with only the sheet bytes rewritten. A login-gated "process modification" path
(`api/v2/toolcontrol/validate`, `api/v2/tools`) is analytics/validation only; the bytes are made in the browser.
Script: `scripts/game_font.py` (export / cells / import / restore). Notes: `NOTES-raw.md`.
Status: decoded, disc-verified (sheet renders; export->import round-trip is byte-identical), loader found.

## 1. The font sheet

| | |
|---|---|
| pixel data | WA_MRG `0xB48000` = in-file sector 0x1690 (5776), disc LBA 15878; 21504 B |
| format | 256x168, 4bpp, 128-byte rows, low nibble = left pixel (`ppb:2`) |
| CLUT | WA_MRG `0xB60800` (sector 0x16C1 +0, LBA 15927): 16 x u16 BGR555 LE |
| stock CLUT | `0000 DEF7 C631 B18C A529 94A5 8C63 8421 A8A3 D107 A06A A470 99A6 9560 88EC 8010` (0 = transparent; 1..7 a white->grey ramp used by the glyphs; 8..15 tinted entries; all opaque entries have STP set) |
| small grid | cells 8x12, 16 columns x 6 rows, origin (0,0) -> sheet rows 0..71 |
| large grid | cells 16x16, 16 columns x 6 rows, origin (0,72) -> rows 72..167 |

Character order (both grids, row by row; `None` = unused cell; the large grid puts `←`, `→` and the
48-px-wide `END` word in row 3 cells 11..15):

    row0  ! " # $ % & ' ( ) * + , - . / 0
    row1  1 2 3 4 5 6 7 8 9 : ; < = > ? -
    row2  A B C D E F G H I J K L M N O P
    row3  Q R S T U V W X Y Z - - - - - -      (large: Q..Z, space, ←, →, E N D)
    row4  ␠ a b c d e f g h i j k l m n o
    row5  p q r s t u v w x y z ␠ ␠ α β γ

The site's constants: `Vt=11829248` (0xB48000), `Yt=21504`, `Kt=256`, `Zt=168`, `Qt=11929344` (0xB60800),
`ea=32`; `unpackIndices` reads `lo = b & 15` first, `packIndices` writes `lo | hi<<4`; the palette is read
BGR555 with `c<<3 | c>>2` expansion and an `stp` flag.

Tool behaviour:
- `regenerate` copies the original index sheet, then for every cell draws the character with the chosen font
  on a black canvas (font size `0.92*cellH*scale`, centred, baseline `+1+yOffset`), maps each pixel to the
  nearest CLUT colour (so the glyphs end up in the white->grey ramp 1..7 and background in 0 = transparent),
  and `drawEndWordSpecial` redraws the `END` word (48 px wide from cell 13 of row 3, text 32 px right-aligned,
  8 px on the left filled with the first STP entry).
- `downloadModified` writes only `0xB48000..0xB4D3FF`; the CLUT is never changed by the site (the script can,
  with `--palette`).
- The preview component (`PreviewZone`) shows the sheet with `ImagePanel {256x168, 16 colours, bytes_width 128,
  body 11829248, palette 11929344, ppb 2}` plus a `TextGenerator` demo string.

## 2. What the game does with it

- The sheet is part of a 54-sector UI block loaded once at boot: `func_80043960` (matched C) calls
  `func_80014E1C(0, 0, 0x1690, 0x36, func_80043328, 0, 0)` — sectors 0x1690..0x16C5 = WA_MRG
  `0xB48000..0xB63000`: font (0xB48000, 0x5400 B), UI icon sheet (0xB50000, 256x160 4bpp: attribute/type icons,
  "FIELD"/"MEADOW"/"FOREST" labels, LP/COM/2P boxes, button glyphs), a 0x1000-byte CLUT block at 0xB60000
  (128 x 16-colour palettes, font CLUT = entry 0x40 at +0x800) and the remaining space up to the duel overlay.
- `func_80043328` is the load callback, a 4-phase LoadImage2 state machine: phase 0 queues the 0x18000-byte
  pixel block (font + icons) from the load buffer `D_8009B118`; phase 2 uploads the CLUT block as rect
  (512, 248, 256, 8) (0x1000 B) — so the font CLUT (row 4 of that block) is VRAM CLUT (512, 252); phase 3 uploads
  a 0x800-byte rect (640, 232, 16, 8) from buffer+0x1000, then a 0x1800-byte tail. The VRAM x/y of the 4bpp
  pixel block are set through record fields (+0x30 = 0x280, +4 = 0x40, +6 = 0x10) that are not decoded here.
- Glyph lookup: the text machine works in the game's frequency-ordered character codes (`'A'` = 24,
  `'B'` = 45, `'a'` = 3, `'0'` = 56, `'!'` = 23 — F97 / `gText_adwGlyphCodeTable` at 0x801D9000 maps Shift-JIS
  to those codes); the code -> sheet-cell step (row-major cell order above) goes through a table the decomp has
  not named yet. Text records default to an 8x12 cell (`TextBox_InitRecord`, 0x80035AF0); the 16x16 set is the
  duel overlay's big text (LP digits, "END", the arrows).
- Consequences: fixed 8x12 / 16x16 cells, 16-colour palette shared by both grids, transparent index 0. A
  proportional font is impossible without changing the text machine's advance (8 px cell width).

## 3. Recomp options

- Pure data: patch the 21504 bytes at WA_MRG 0xB48000 (and optionally the CLUT at 0xB60800) in the disc image
  the recomp streams, or hook the boot-time load: the block lands in the buffer at `D_8009B118` before
  `func_80043328` phase 0 runs, so a frame hook that detects the queued load (or a `LoadImage2` source swap
  keyed on size 0x18000, same trick as `psx_card_skins.c`'s LoadImage stub) can point the DMA at a host-filled
  sheet. Boot-only, so no per-frame re-assert is needed after the upload — but re-upload if the game ever
  re-runs `func_80043960(arg0)` (it does on some screen transitions: the function is also the FntOpen/debug init).
- Native replacement: render TTF glyphs on the host into the 8x12 / 16x16 cells (the recomp already ships
  `psx_fusion_font` with an 8x12 duel font), quantise onto CLUT entries 1..7, and hand the sheet to the same
  swap. Extra characters (accents) need free cells: rows 1/3 have 7 unused small cells.

## 4. Decomp findings (proposed)

- WA_MRG `0xB48000` (sector 0x1690, 0x36 sectors) | boot UI texture block: 256x168 4bpp text font (two grids
  8x12 and 16x16, 16 cols x 6 rows, order `!"#$%&'()*+,-./0 1..9:;<=>? A..P Q..Z ␠a..o p..z␠␠αβγ`), icon sheet at
  +0x8000 (256x160 4bpp), CLUT block at +0x18000 (0x1000 B, font CLUT at +0x18800); loaded by `func_80043960` ->
  `func_80014E1C(0,0,0x1690,0x36,func_80043328)` | `WA_UiTextures`, `func_80043328` = `Ui_UploadBootTextures`
- `func_80043328` | LoadImage2 phases: CLUT block -> VRAM (512,248,256,8); 0x800 B -> (640,232,16,8) |
  (facts; font CLUT = VRAM (512,252))

## 5. Open questions

- Exact VRAM x/y of the 4bpp font/icon pixel block (phase 0 record fields 0x280/0x40/0x10 and the `D_8009B0F4`
  flag bits need a live trace).
- The site's V.20260729 chunk contains a `GridCharEditor` for remapping characters per cell, but the mapping is
  only used to decide which character is drawn into which cell; the game's code table is not changed, so
  "including accented letters" means drawing them into an unused cell and typing that cell's Shift-JIS code.
