# Thumbnail tool (dialog portraits)

Route: `extend/tools/image/thumbnail` (tool version V.220111). Input: WA_MRG.MRG (`.mrg`,
37,748,736..39,845,888 bytes) plus any image (`image/*`, up to 12 MB). Replaces one of the 25
48x48 character portraits that dialog boxes show next to the text, and prints the text-control
code that puts each portrait in a dialog. Everything is client-side; the file is downloaded back.
Script: `scripts/dialog_thumbs.py` (inspect / export / import / restore). Notes: `NOTES-raw.md`.
Status: decoded, disc-verified (all 25 portraits render), script round-trips byte-for-byte.

## 1. The portrait file

| | |
|---|---|
| WA_MRG offset | `0xF35000 + 2432*(n-1)`, n = 1..25 |
| in-file sector / disc LBA | 0x1E6A..0x1E87 (7786..7815) / 17888..17917; 30 sectors, last 640 bytes of the file are `FF` padding |
| tile layout | `+0` 48x48 8bpp indices, 48-byte rows (2304 B); `+2304` 64-entry CLUT, u16 BGR555 little endian (128 B) |
| CLUT encoding | bit0-4 R, 5-9 G, 10-14 B, bit15 STP. `0x0000` = transparent; every stock opaque entry has bit 15 set (64/64) |
| pixel indices | stock tiles use 1..63 (index 0 is never used) |
| dialog code | `F6 xx 00` with `xx = 0x40 + n` (`[F6 41 00]` = portrait 1 ... `[F6 59 00]` = portrait 25) |

Order on disc (verified by rendering): 1 Simon, 2 Jono, 3 Teana, 4 Seto, 5 Heishin, 6 Kepura?, 7 Isis-like
priestess, 8 Mage Soldier ... 25 (see `scripts/dialog_thumbs.py export`). The same 2432-byte tile format is
used by the free-duel opponent portraits (F121: 40 tiles, but those live inside the 0x1E88 load, not at its
first byte — see open questions).

Tool behaviour (`Editor` component, `ImageConverter` from chunk-common):
- reads the tile through `ImagePanel` with `config {width 48, height 48, num_colors 64, bytes_width 48, body_offset 0xF35000+2432*(n-1), pallete_offset 15948032+2432*(n-1)}` (15948032 = 0xF35900 = body + 2304);
- the uploaded image is drawn on a 48x48 canvas, each channel rounded to 5 bits, a histogram picks the 64 most frequent colours (no dithering), the palette is sorted by RGB value, every pixel maps to the nearest palette entry;
- `keep_black`: pure black (0,0,0) is replaced by (8,8,8) so it does not collide with the transparent index, and the site writes bit 15 (`"1"` prefix) on every non-black entry; black itself is written as `0x0421`-style near-black with STP. "This tool don't use transparent color", so no alpha survives;
- `setNewHeader` packs `lo = G[2:5]<<5 | R>>3`, `hi = STP | B>>3<<2 | G>>6` (standard PSX 15-bit), `setNewBody` writes `body[x + 48*y]`;
- `saveAs` downloads the whole modified WA_MRG.MRG. Nothing in SLUS_014.11 changes.

## 2. What the game does with it

- The text machine (`TextBox_BuildStep` 0x800393B0, F98) dispatches control byte `0xF6` to
  `func_80038EB0`. That handler consumes two more bytes: `idx` (0x41..0x59 = portrait, values < 0x41 are
  other face-box commands) and a flags byte (bit 0x80 open/close, 0x40, 0x20, 0x10 + bits 1-2 = colour slot,
  0x08 = alternate position 0x400, 0x02/0x01 = side / animation), and fills a 0x4C-byte face-box record in
  the `D_800EB010` table (+0x30 = idx, +0x3C = side, +0x34/+0x40..+0x44 = position/tween: x 0x178 or -0x38,
  y 0xB2, 0x10, ...). It calls `func_80039F44` / `func_80039FD4` (record init / kill) and stores the record
  pointer at `gp+0x420`.
- Portrait n is therefore selected by `idx - 0x40`; the sprite that draws it is set up elsewhere (the record
  consumer, not yet traced) from a VRAM copy of the 2432-byte tile. Which function reads sector 0x1E6A is not
  visible in the EXE: no `0x1E6A` / `7786` immediate exists in SLUS_014.11 (scanned `li/addiu/ori/.word` and raw
  u16), so the load is issued by a disc-loaded module (campaign/cutscene code) or computed from a base.
- Consequences: 25 slots, fixed 48x48, 64 colours, opaque. Changing a portrait changes it for every dialog
  that uses that code (the site's hint: "use the codes under each image in the text editor").

## 3. Recomp options

- Data-only mod: no code changes. Either patch the tile in the WA_MRG image the recomp streams from (offset
  above; `scripts/dialog_thumbs.py import`), or, like `src/psx_card_skins.c`, intercept `LoadImage`
  (0x8007F978) when the rect is the face-box upload and swap the source pointer to a host-filled 48x48 +
  64-CLUT buffer. The rect used for portraits still has to be measured (F121 gives the free-duel geometry:
  48x48 8bpp = 24 halfwords wide; CLUTs 64 wide).
- A friendlier version: watch the face-box record table `D_800EB010` for +0x30 in 0x41..0x59 and feed a PNG
  per portrait, which also allows more than 25 portraits if the sprite's texture-page/CLUT fields are
  redirected to a reclaimed VRAM area.

## 4. Decomp findings (proposed)

- `0xF35000` in WA_MRG (sector 0x1E6A, 30 sectors) | 25 dialog portraits, 2432 B each = 48x48 8bpp + 64-entry
  CLUT (same tile format as the free-duel portraits of F121), `FF`-padded to 30 sectors; verified by rendering
  all 25 | `WA_DialogPortraits` (disc region)
- `func_80038EB0` | text control `F6 idx flags` handler: fills a 0x4C face-box record in `D_800EB010`;
  `idx >= 0x41` selects a portrait (idx-0x40 = tile 1..25), the flags byte selects side/position/colour slot |
  `TextBox_HandleFaceControl` / `gTextBox_aFaceRecords`

## 5. Open questions

- Which code issues the CD read of sector 0x1E6A and the LoadImage of the tile (VRAM x/y)? Not in the EXE's
  literal sector list (0x1690, 0x1E88, 0x1EDF, 0x1F2F, 0x1F85, 0x1FA7, 0x1FD9+n, 0x2115, 0x2147, 0x2157, 0x2189).
- The 0x1E88 block (free-duel portraits, 0x57 sectors) does not start with raw 2432-byte tiles (rendering
  its first bytes gives noise), so the portrait buffer sits at an offset inside that load.
- Server side: only the analytics POST `api/v2/tools` (tipo 12). No presets or server data are involved.
