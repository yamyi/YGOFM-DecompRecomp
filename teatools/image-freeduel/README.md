# FREE DUEL image tool (opponent portraits + grid names)

Route: `extend/tools/image/freeduel`. Inputs: SLUS_014.11 (`.11`, 1,677,721..2,097,152
bytes) and WA_MRG.MRG (`.mrg`, 37,748,736..39,845,888 bytes), plus a PNG/BMP 48x48 (quantized
to 64 colours by the page). Two independent outputs: SAVE SLUS (names) and SAVE WA_MRG.MRG
(portraits). Client-side only.
Script: `scripts/freeduel_portraits.py` (inspect / export / import / restore / verify tiles;
names / rename / restore-names; export-screen). Raw notes: `NOTES-raw.md`.
Status: decoded, disc-verified against decomp F121/F122 and the recomp's free-duel mod, PNG
round trip and byte-identical restore tested on copies, not yet built as a mod.

The FREE DUEL screen is an 8x5 grid: cell `row*5+col` = duelist id (0 = the Build Deck tile,
1 Simon Muran ... 37 DarkNite, 38 Nitemare, 39 Duel Master K). The tool swaps a cell's 48x48
portrait and its name.

## 1. Portraits (WA_MRG.MRG)

| | |
|---|---|
| tile i | WA offset `0xF55000 + 2432*i`, i = 0..39 (site: `16076800 + 2432*i`) |
| in-file sector | 0x1EAA (= free-duel load 0x1E88 + 34), disc LBA 17952 |
| tile layout | 2304 bytes 48x48 8bpp indices 0..63, then 128 bytes = 64-entry CLUT (15-bit LE) |
| stock CLUT convention | every entry has the STP bit set; black stored as 0x8000 (opaque) |
| end | tile 39 ends at 0xF6CC00; zeros follow until the load ends at 0xF6F800 |

Load and upload (decomp F122/F121, `src/func_8003B9BC.c`, `src/func_8003B808.c`):

    Main_InitFreeDuelMenu (0x8003B9BC):  func_80014E1C(0, 0, 0x1E88, 0x57, func_8003B808, 0, 0)
                                          FreeDuel_Init(*(u32*)0x80010000)      /* arena 0 = 0x80100000 */

`func_8003B808` is the stream callback; its five arms split the 87 sectors:

| arm | sectors | destination |
|---|---|---|
| 0 | 0..31 | VRAM stream from (0,256), 64x16 per sector: the screen's own backdrop, a 128x512 8bpp strip (`export-screen`) |
| 1 | 32 | RAM (CLUT sector) |
| 2 | -- | `LoadImage2` (0,240,256,4) = backdrop CLUT; then sector 33 -> 0x801AF000 (the cursor sparkle texture, F86) |
| 3 | 34..81 | 0x18000 bytes -> `D_80010000` = 0x80100000: **the 40 portrait tiles** (0x17C00 used) |
| 4 | 82..86 | 0x2800 bytes -> `*(u32*)(D_800100A8 + 0x130)` (not identified) |

`FreeDuel_Init` (0x8016824C, free-duel module) then uploads tile i's image to VRAM page 18
(i < 25: x = 128 + 24*(i%5), y = 256 + 48*(i/5)) or page 20 (i >= 25: x = 256 + 24*col) and its
CLUT to (128 + 64*(i>>4), 496 + (i&15)), and spawns a 48x48 sprite per available cell with
u = (i%5)*48, v = (i/5)*48. The recomp's `psx_free_duel_rows.c` already patches those loops.

Consequences: 64 colours per portrait, exactly 48x48, no transparency (the tiles are solid
squares; the site keeps black as black). Because the tiles are re-read from disc on every
entry to the screen, a runtime mod must act after the load and before/at the upload.

## 2. Names (SLUS_014.11)

| | |
|---|---|
| string ids | 808..847 = `0x8328 + row*5+col` (`FreeDuel_PlaceCursor`, F124) |
| offset table | `gText_aGlobalOffsets` 0x801D5800 = SLUS file 0x1C6000, u16 `off[id]` |
| strings | 0x801D0000 + off = SLUS file 0x1C0800 + off; stock ids 808..847 occupy 0x8BD0..0x8D9A (RAM 0x801D8BD0..0x801D8D9A) |
| budget | 458 bytes including 40 `FF` terminators = 418 characters; string 848 starts right after |
| charset | the global-bank frequency table: `01 e, 02 t, 03 a, 04 o, 05 i, 06 n, 07 s, 08 r, 09 h, 0A l, 0B ., 0C d, 0D u, 0E m ...` (full map in the script) |

Stock names (verified by decoding the table): Build Deck, Simon Muran, Teana, Jono, Villager1,
Villager2, Villager3, Seto, Heishin, Rex Raptor, Weevil Underwood, Mai Valentine, Bandit
Keith, Shadi, Yami Bakura, Pegasus, Isis, Kaiba, Mage Soldier, Jono 2nd, Teana 2nd, Ocean
Mage, High Mage Secmeton, Forest Mage, High Mage Anubisius, Mountain Mage, High Mage Atenza,
Desert Mage, High Mage Martis, Meadow Mage, High Mage Kepura, Labyrinth Mage, Seto 2nd,
Guardian Sebek, Guardian Neku, Heishin 2nd, Seto 3rd, DarkNite, Nitemare, Duel Master K.

The site's `setNames` repacks all 40 names contiguously from the stock start (0x8BD0),
rewrites `off[808..847]`, and refuses to save when the total exceeds the budget (its hint says
"488 chars"; the real figure computed by its own code on the US SLUS is 418). Bytes after the
new pack (up to 0x8D9A) are left as they were. The same table serves card names (ids 1..722,
i.e. 0x8001..) and card-type names (768..791) -- see `psx_card_skins.c` in the recomp.

## 3. Site details

- `FaceFoe` renders a tile straight from `body_offset` / `pallete_offset` (decode as in the
  other image tools); `ImageConverter` quantizes with `keep_black`, so black stays (8,8,8).
- `setNewHeader` writes STP on all non-black colours -- matches the stock tiles.
- `readName` stops at byte >= 253 (FF terminator) or 50 characters; unknown codes are dropped.
- Server side: only the analytics POST (`api/v2/tools`, tipo 16).

## 4. Recomp options

- Portraits, disc-level: `scripts/freeduel_portraits.py import` on WA_MRG.MRG inside the .bin.
- Portraits, runtime: the tiles sit unmodified in RAM at 0x80100000 + 2432*i from the end
  of the load until `FreeDuel_Init` uploads them. A mod can overwrite the tile bytes there
  from a hook on `FreeDuel_Init`'s entry (0x8016824C; `psx_mod_register_function_entry_plugin`,
  guarded by the module signature like `psx_free_duel_rows.c`), or swap the upload source per
  rect in a `LoadImage` stub (the `psx_card_skins.c` idiom; the rects are
  `(128+24c, 256+48r, 24, 48)` / `(256+24c, ..)` and CLUT `(128+64(i>>4), 496+(i&15), 64, 1)`).
  That is the natural base for the parked "duelist pack" feature (portrait.png per duelist).
- Names, runtime: repoint `off[808+i]` (u16 at 0x801D5800 + 2*(808+i)) to a fresh string in
  reclaimed RAM (`psx_card_skins.c` uses 0x801D9C00..0x801DA000 for card names) and re-assert
  per frame -- no byte budget, no repacking. Base-EXE data, but the table is re-streamed per
  screen, hence the per-frame check.

## 5. Decomp findings (proposed)

- `0x8003B808` | free-duel load callback, 5-way jump table: 32 sectors -> VRAM (0,256) stream (screen backdrop), sector 32 CLUT -> (0,240), sector 33 -> 0x801AF000, 48 sectors -> `D_80010000` (portrait tiles), 5 sectors -> `*(D_800100A8+0x130)` | `FreeDuel_LoadCb`
- WA sector 0x1EAA (0xF55000) | the 40 portrait tiles, 2432 B each (48x48 8bpp + 64-entry CLUT, STP on every entry); F121's "buffer" = arena 0 holds them from load offset 34 sectors | (disc fact, refines F121/F123)
- WA sector 0x1E88 (0xF44000) | free-duel screen backdrop: 128x512 8bpp strip + CLUT sector, same packing as the cutscene pictures | (disc fact)
- `0x801D8BD0..0x801D8D9A` | global-bank strings 808..847 = free-duel grid names, id = cell index | (fact; `gText_aGlobalOffsets` confirmed as F118 describes)
- `D_801AF000` | 2 KB texture streamed with the free-duel screen (sparkle, F86) | `gFreeDuel_SparkleTex`

## 6. Open questions

- What arm 4's 5 sectors are and where `*(D_800100A8+0x130)` points.
- Whether the backdrop strip's second CLUT rows (241..243, non-zero on this load) are used.
