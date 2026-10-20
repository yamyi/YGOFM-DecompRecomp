# Campaign Characters tool (dialogue portraits)

Route: `extend/tools/image/campaign/characters` (page version V.220214). Input:
**WA_MRG.MRG** (`.mrg`, 37,748,735..39,845,888 bytes) and an image (`image/*`, up to
30 MB; the page asks for a 256-colour PNG/BMP of the template's size). Client-side apart
from analytics (`api/v2/tools` tipo 8) and `GET api/v2/tools/newtemplates` (extra
templates for logged-in users; not visible without a session). Purpose: replace one of the
64 campaign dialogue portraits (the character pictures shown with the `[F6 xx 00]` text
code) by drawing on a template canvas; the tool cuts the canvas into the game's tiles,
builds the two palettes, zeroes the animated parts and writes a canned animation script.
Status: decoded, disc-verified, loader + VRAM map traced, offline clone written, not yet
built as a recomp mod.

Script: `scripts/campaign_portraits.py` (list / dump / apply / restore on a WA_MRG copy;
`scripts/templates.json` holds the six template chunk tables, animation scripts and the
character list extracted from the site JS). Raw notes: `NOTES-raw.md`.

## 1. The 64 portrait blocks in WA_MRG.MRG

    block(id) = 0x1DC0000 + 0x19000 * (id - 1)      id = 1..64, 50 sectors each
    in-file sector = 15232 + 50*(id-1)   (0x3B80 + 0x32*(id-1)),  disc LBA = 25334 + 50*(id-1)

| block offset | size | content | VRAM |
|---|---|---|---|
| 0x00000 | 0x18000 | 8bpp image as a 128-byte-wide column, 768 rows = three 128x256 pages | pages `(832 - 192*side, 256)`, `(896 - 192*side, 256)`, `(960 - 192*side, 256)` |
| 0x18000 | 0x200 | CLUT A: 256 x 15-bit, STP bit clear | `(512, 240 + 2*side)` |
| 0x18200 | 0x200 | CLUT B: the same colours with STP set | `(512, 241 + 2*side)` |
| 0x18400 | 0x400 | zero | - |
| 0x18800 | ~0x100..0x200 used, 0x800 read | portrait sprite / animation script | RAM `0x801AF000` (side 0) or `0x801AF800` (side 1) |
| 0x18900.. | | 0xFF padding to the end of the 50th sector | |

`side` is the loader object's byte +0x3C (0 or 1: which of the two dialogue slots the
character occupies); it moves the three pages from (832..1024, 256..512) to
(640..832, 256..512) and the CLUT pair from rows 240/241 to 242/243.

The tool's constants: `body_offset = 0x1DC0000 + 102400*(id-1)`, palettes at
`31293440 + 102400*(id-1)` (= block + 0x18000) and +512, script at palette + 2048
(= block + 0x18800). Verified stock bytes for id 1: image rows 0..511 are used (two states,
pages 0..1), rows 512..767 and 0x17000..0x17FFF are zero, CLUT A starts `0000 5BFF 53DF 7FBB ...`, CLUT B `0000 DBFF
D3DF FFBB ...` (A | 0x8000), script `10 00 16 00 00 ... 1C 00 1E 00 ...` = the tool's
template-1 `com` array.

Character ids (tool list, `[F6 id 00]` in dialogue text): 1 Simon Muran, 2 Jono, 3 Teana,
4 Seto, 5 empty, 6 Dark Shrine Guardian, 7 Heishin, 8 Egyptian card trader, 9 Lady of the
Palace, 10 beaten Simon, 11 empty, 12 Pharaoh Atem, 13 Joey, 14 Kaiba, 15 Shadi, 16 Rex,
17 Weevil, 18 Mai, 19 Keith, 20 Bakura, 21 Pegasus, 22 Tea card trader, 23 Catacomb Keeper,
24 Mage Soldier, 25 Ocean Mage, 26 Secmeton, 27 Forest Mage, 28 Anubisius, 29 Mountain Mage,
30 Atenza, 31 Desert Mage, 32 Martis, 33 Meadow Mage, 34 Kepura, 35 Sebek, 36 Neku,
37 DarkNite, 38 Nitemare, 39..41 empty, 42 Tournament Host, 43..45 Villagers, 46 Labyrinth
Mage, 47 Isis, 48..64 the "defeated" faces (Jono, Teana, Seto, Heishin, Kaiba, Rex, Weevil,
Mai, Keith, Bakura, Pegasus, DarkNite, Villagers 1..3, Labyrinth Mage, Isis).
`campaign_portraits.py list` prints ids with offsets and LBAs.

## 2. What the tool writes

* Image: the canvas (template size, e.g. 368x160 for template 1) is quantised to 256
  colours (5-bit rounding, most frequent colours, nearest match; opaque black -> (8,8,8);
  transparent -> colour 0) and cut into the block through the template's chunk table
  (`data(x,y) <- canvas(x,y)`, w x h, all in 128-byte-row coordinates). Clicking a colour
  in the preview (`makeTrasparent`) makes it transparent: those entries are removed from the
  palette, indices above shift down by one, and matching pixels become 0.
* CLUT A at +0x18000 with STP = 0, CLUT B at +0x18200 with STP = 1 (`setNewHeader(off, pal,
  "0","1")` then default "1").
* `cleanBody`: the template's `da` rectangles (eyes/mouth animation frames the template
  does not model) are zeroed.
* `setNewCommand`: the template's `com` byte array (200..496 bytes) is written at +0x18800.

Templates (chunk count, canvas, animated `da` rectangles): 1 Simon Muran 2 states (18,
368x160), 2 H.M. Anubisius 1 state (7, 232x232), 3 Atem 1 state (10, 184x200), 4 Bakura
2 states eyes+mouth (21, 416x168), 5 Rex Raptor 2 states (17, 320x176), 6 Pegasus 2 states
(18, 496x192). "2 states" = the block holds two portraits (normal + a second expression,
pages 0..1 vs 1..2 / rows 0..255 vs 256..511 in column space). Any template can be forced
onto any character (the page says so), the result is only correct if the character's
script draws the same tiles; the shipped scripts are what make the template layouts work.

The script format was only sampled: it starts with u16 little-endian offsets into itself
(`0x0010, 0x0016, 0, ...`), leading to short tables and to animation strips of
`(delay, u16 record offset)` triples ending in 0xFF (Simon: `0,112 3,112 3,122 3,132 3,122
3,112 FF` = an eye-blink over three 10-byte records), and to 16-byte sprite/piece records
(`04 10 00 00 D0 80 0D C0 20 C6 ...`). The second state repeats the tables with +16/+0x10
offsets. Not needed to replace a portrait if a template script is reused.

## 3. What the game does with it

`func_8003A560` (proposed `Campaign_ShowPortrait`; called with the dialogue object whose
+0x30 is the character id and +0x3C the side) first checks a 4-entry cache: `D_8015C410[i]`
holds the id cached in slot i, the pixels live at `arena0 + 0x63040 - 0x18C10*i`
(0x80163040 downwards). On a hit it uploads from RAM with `LoadImage` (0x8007F978):
`rect(832 - 192*side, 256, 192, 256)` from the cache block (row-major there, 384 bytes per
row) and `rect(512, 240 + 2*side, 256, 2)` from cache+0x18000, then copies 0x800 bytes from
cache+0x18400 to `0x801AF000` / `0x801AF800`. On a miss:

    8003A700  a2 = id*50 + 0x3B4E            ; = 0x3B80 + 50*(id-1)
    8003A724  a3 = 0x32                       ; 50 sectors
    8003A730  func_80014E1C(0, 0, a2, 0x32, func_8003A01C, 0, 0)
    8003A744  loader->0x38 = 0x801AF000 (or 0x801AF800 if side)   ; script destination
    8003A750  loader->0x3C = side

and the stage callback `func_8003A01C` programs: stage 0: 0x18000 bytes streamed to VRAM
from `(832 - 192*side, 256)` as 64x16 rects in page-column order (`func_80013C28`); stage 1:
one sector (block +0x18000) to the staging buffer; stage 2: `LoadImage2((512, 240+2*side,
256, 2), staging)` and one sector (block +0x18800) to RAM at `loader->0x38`. 48 + 1 + 1 = 50.
The 2 KB at +0x18800 is therefore the whole script the game keeps; +0x18400..0x18800 is
never read from disc. The dialogue renderer then draws pieces from those pages with CLUT
rows 240/241 (side 0) or 242/243 (side 1) following the script at 0x801AF000/0x801AF800.

## 4. Recomp options

1. **VRAM-level replacement (native).** Hook `func_8003A560`'s entry (or the `LoadImage2`
   with rect `(512, 240+2*side, 256, 2)`, which fires once per portrait load, cache hit or
   miss) and, when the id is skinned, upload three 128x256 8bpp pages to
   `(832-192*side .. , 256)` plus the two CLUT rows from a host buffer (PNG -> 256 colours,
   same quantiser as the card-skin mod). Keep the stock script so the pieces animate; for a
   template-style redraw also write the template `com` bytes to `0x801AF000 + 0x800*side`
   after stage 2 (the script is re-read from disc on every miss, and from the cache block
   on hits, so re-assert it in the hook).
2. **Disc-level.** Substitute the 50 sectors at LBA 25334 + 50*(id-1) in the CD path; also
   patch the RAM cache when the id is already resident (compare `D_8015C410[0..3]`).
3. **Data pack.** Ship a modified WA_MRG.MRG produced by `campaign_portraits.py apply`
   (what the site does); the recomp reads the file from the user's disc image.

## 5. Decomp findings (proposed)

* `0x8003A560` | campaign dialogue portrait loader: 4-slot RAM cache (`D_8015C410[4]` ids, blocks at 0x80163040 - 0x18C10*i, uploaded with `LoadImage` 192x256 at (832-192*side,256) + CLUT 256x2 at (512,240+2*side)); on a miss `func_80014E1C(0,0, 50*id + 0x3B4E, 0x32, func_8003A01C)` | `Campaign_ShowPortrait`
* `0x8003A01C` | its 3-stage callback: 0x18000 B streamed to VRAM (832-192*side,256) column, 1 sector CLUT -> (512,240+2*side,256,2), 1 sector script -> loader+0x38 (0x801AF000 / 0x801AF800) | `Campaign_PortraitStage`
* `D_8015C410` | 4 x s8 character id currently held in portrait cache slot i (-1 empty) | `gCampaign_abPortraitCacheID`
* `0x801AF000` / `0x801AF800` | 2 KB portrait animation script per dialogue side | `gCampaign_aPortraitScript`
* WA_MRG `0x1DC0000 + 0x19000*(id-1)` (LBA 25334 + 50*(id-1)) | 64 portrait blocks: 3 pages 8bpp column + CLUT A/B + script at +0x18800 | (facts)

## 6. Open questions

* The script byte format (frame records, piece coordinates) is only partially understood.
* Whether `[F6 xx 00]` is really the text code that triggers `func_8003A560` (the tool's
  claim; the text-engine opcode table was not traced here).
* What the two "states" of a character mean at run time (mouth open/closed vs a second
  expression), and how the game chooses between them.
* Which caller fills the RAM cache slots (the loader only reads from it).
* The reference images `/Assets/img/templates/01..06.png` need a session (302 without one),
  so they are not mirrored; the chunk tables in `scripts/templates.json` are the same data.
