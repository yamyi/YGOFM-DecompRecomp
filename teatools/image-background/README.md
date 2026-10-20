# BACKGROUND tool (static cutscene pictures)

Route: `extend/tools/image/background` (V.220111). Input: WA_MRG.MRG (`.mrg`,
37,748,736..39,845,888 bytes) plus any PNG/BMP of 320x160 (the page quantizes it to 256
colours itself). Everything is client-side; the edited WA_MRG.MRG is downloaded back.
Script: `scripts/cutscene_bg.py` (inspect / export / import / restore / verify; also serves
the BGCOMP and BGMOV tools, which are the same record format with more layers).
Raw session notes: `NOTES-raw.md`.
Status: decoded, disc-verified (renders match the game), PNG round trip and byte-identical
restore tested on a copy, not yet built as a mod.

The tool replaces one of the campaign's full-screen cutscene backdrops (temple front, throne
room, ...). Its list "Background - NN - Pointer [F7 05 NN 00]" numbers them 01..48; NN is the
game's own picture number (a BCD byte in the cutscene script), and on the US disc pictures
01..41 are real while 42..49 are blank placeholders (5 non-zero bytes each, default CLUT).

## 1. The record

One picture = 33 sectors of WA_MRG.MRG, `static NN` at

    WA offset  = 0x10EA800 + NN * 0x10800        (NN = 0..49; NN 0 is blank too)
    in-file sector = 0x21D5 + NN * 0x21          disc LBA = 18763 + NN * 33
    e.g. NN 01: 0x10FB000  sector 0x21F6  LBA 18796   (site: body 0x10FB000, palette 17870848 = 0x110B000)

| in-record | size | content |
|---|---|---|
| +0x0000 | 0x10000 | pixel strip: 512 rows x 128 bytes, 8bpp CLUT indices (= 32 sectors) |
| +0x10000 | 0x200 | 256-entry CLUT, 15-bit `0BBBBBGGGGGRRRRR` little-endian (stock: no STP bits, no zero entries) |
| +0x10200 | 0x600 | zero |

The 320x160 picture is cut into a 128-pixel-wide strip the way it sits in VRAM (each 128-byte
row = one 64-halfword texture row):

| strip x, row (w x h) | canvas x, y | note |
|---|---|---|
| 0, 0 (128x160) | 0, 0 | left third |
| 0, 256 (128x160) | 128, 0 | middle third |
| 0, 416 (64x80) | 256, 0 | right third, top half |
| 64, 416 (64x80) | 256, 80 | right third, bottom half |

Rows 160..255 and 496..511 are zero. Stock bytes checked on the disc: NN 01 row 0 starts
`30 30 35 35 35 38 38 38`, its CLUT `7a 6b 7a 80 ...` is NOT at 0x110B800 (that is NN 02's
first pixel row) but at 0x110B000 -- the site's decimal constant 17870848 decodes to 0x110B000.

## 2. What the game does with it

The cutscene is a bytecode/text script (decomp F111). The command the site prints as
`F7 05 NN MM` reaches `Script_OpShowImage` (0x8002E730, script opcode 5) with the u16 parameter
in `D_8009B270`; it allocates the 320x160 display quad (`func_80040510(rec,0,0,0x140,0xA0,...)`)
and calls the picture request with `param & 0xFFF`:

```c
/* src/func_8002DF2C.c (matched) -- 0x8002DF2C */
v1   = ((code >> 4) & 0xF) * 10 + (code & 0xF);   /* NN is BCD */
mode = code >> 8;                                  /* MM: 0 static, 1 composite, 2 moving */
s0 = 0x21, a2 = 0;        /* mode 0 */
s0 = 0x51, a2 = 0x672;    /* mode 1 */
s0 = 0x71, a2 = 0x13BC;   /* mode 2 */
v0 = reinit_d800e9e60_obj(0, 0, a2 + v1 * s0 + 0x21D5, s0, func_8002DDFC, 0, 0);  /* CD stream */
v0->f38 = s0 - 1;                                  /* pixel sectors before the CLUT sector */
```

So the picture number is a sector index: `0x21D5 + NN*33` for static pictures. The load is the
generic disc stream (`func_80014E1C` / `reinit_d800e9e60_obj` -> `func_80013998`, polled by
`func_80013C28`), and `func_8002DDFC` (0x8002DDFC, matched) is its callback:

| callback state | effect |
|---|---|
| 0 (start) | stream mode 2: each 2048-byte sector is `LoadImage2`'d as a 64x16 rect starting at VRAM (0,256), double-buffered from `D_8009B118` / `+0x800`; byte budget `f1C = f38 << 11` = 32 sectors |
| 1 | last sector goes to RAM (`f1C = 0x800`) |
| 2 (end) | `LoadImage2` rect (0,240) 256x4 from that sector = the CLUT (row 240; rows 241..243 get the zero tail) |

`func_80013C28` state 2 advances the rect by `y += 16`, wrapping at 512 back to 256 with
`x += 64`: sectors 0..15 fill VRAM x 0..63 / y 256..511 (strip rows 0..255), sectors 16..31
fill x 64..127 (strip rows 256..511). That is why the picture is stored as 128-byte rows and why
the middle third starts at strip row 256: it is the second 8bpp texture column. The display quad
reads it as an 8bpp texture at texpage (0,256)/(64,256) with the CLUT at (0,240).

Consequences: the slot is fixed at 33 sectors and 320x160x8bpp -- no other size fits; NN is
BCD (`0x12` = 12), values 50..99 would index into the composite set that follows at sector
0x2847; the CLUT row is shared VRAM space (rows 240..243), so pictures cannot keep more than
one palette; opaque black must not be CLUT word 0 (transparent) -- the site stores it as
(8,8,8) = 0x0421, stock data uses 0x0421-like darks or 0x8000.

## 3. Site details worth knowing

- `ImagePanel` decodes CLUT words with `r=(lo&0x1F)<<3, g=(hi&3)<<6|(lo&0xE0)>>2,
  b=(hi&0x7C)<<1`, alpha 0 only when the word is 0. `ImageConverter` histograms the uploaded
  image at 5-bit precision, keeps the 256 most frequent colours, and `keep_black` turns pure
  black into (8,8,8) before writing (`setNewHeader` also sets the STP bit on every non-black
  colour it writes, which stock data does not have -- harmless for an opaque backdrop).
- Only the four chunk rectangles are written; the zero rows stay untouched.
- `getPointer` prints the BCD byte as the two decimal digits of the list index.
- Server side: only the analytics POST to `api/v2/tools` (tipo 7) on save.

## 4. Recomp options

1. Disc-level (no code): patch WA_MRG.MRG inside the .bin with `scripts/cutscene_bg.py import`
   and point the recomp at the modified cue/bin. Same format, same size -- the safest route.
2. Runtime swap at upload time, the `psx_card_skins.c` idiom: the 32 pixel rects and the CLUT
   rect all pass through `LoadImage2` (0x80081DE8) with distinctive rects
   `(64k, 256+16j, 64, 16)` and `(0, 240, 256, 4)`; a stub on LoadImage2's entry can swap the
   SOURCE pointer to a mod buffer when the current picture code (kept by `func_8002DF2C` in
   `D_800EAE98->f3C`) is one the player has skinned. Hook `func_8002DF2C` entry with
   `psx_mod_register_function_entry_plugin` to learn `(mode, NN)` as the request is made.
3. Native replacement: after the load completes, upload a mod-supplied 128x512 8bpp strip +
   CLUT to VRAM (0..127, 256..511) / (0,240) yourself; simpler but must beat the fade-in.
   Higher resolutions would need renderer-side texture replacement, which this session did not
   find in psxrecomp.

## 5. Decomp findings (proposed)

- `0x8002DF2C` | picture request: BCD low byte x stride + base (0x21/0, 0x51/0x672, 0x71/0x13BC by mode byte) + 0x21D5 = WA_MRG sector; starts a `stride`-sector CD stream with `func_8002DDFC`; stashes the raw code in `obj->f3C` | `Script_RequestPicture`
- `0x8002DDFC` | its stream callback: state 0 = VRAM stream rect (0,256) 64x16 from the sector double buffer, 1 = final sector to RAM, 2 = `LoadImage2` (0,240,256,4) = CLUT | `Script_PictureStreamCb`
- `func_80013C28` state 2 | per-sector rect stepping proven against picture layout: y += 16, wrap 512 -> 256 with x += 64 (16-sector, 64-halfword columns) | (fact)
- WA_MRG sector 0x21D5 | picture table: 50 x 33-sector static (NN 42..49 blank), then 42 x 81 composite at 0x2847, then 13 x 113 moving at 0x3591, then character sprite sheets at 0x3B52 | (disc facts)
- `D_8009B270` | u16 script command parameter (`& 0xFFF` = picture code; bit 0x4000 tested in `Script_OpShowImage`) | `gScript_wParam`
- `D_800EAE98` | cutscene picture object (`+0x3C` = current picture code) | `gScript_PictureObj`
- `D_8009B118` | CD stream sector double buffer base | `gCd_pSectorBuf`

## 6. Open questions

- Which text-stream escape pushes the `F7 05` parameter into `D_8009B270` was not traced
  (the site's "pointer" notation is taken at face value; `gScript_apfnCommand` 0x80090C50 has
  24 handlers).
- The display quad's constants in `Script_OpShowImage` (`0x17`, `0xF4`) were not decoded.
- `Script_OpShowImage`'s `MoveImage(&{0 or 320, 0, 320, 160}, 0x1C0, 0x100)` path copies the
  current frame to VRAM (448,256) -- presumably the cross-fade staging area; not verified.
