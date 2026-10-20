# Cards / "specsmix" tool — image half

Route: `extend/tools/image/specsmix` (chunk `cards.0ad4f385.js`, V.260517). Inputs: WA_MRG.MRG (`.mrg`,
37,748,735..39,845,888 bytes), SLUS_014.11 (`.11`, 1,782,579..2,097,152 bytes) and PNG/BMP images (up to
20 MB). The page is the site's full card editor: per card it shows the library art, the baked title, the
40x32 thumbnail, the card frame with the stats/name overlaid, and edits names, descriptions, ATK/DEF/type/
level/attribute (SLUS) plus price/password (WA). This folder documents the **image** features and the WA
tables; the SLUS text/stat editing is the `cardsdata` tool's territory (offsets listed in `NOTES-raw.md`).
Script: `scripts/card_images.py` (inspect / export / import / price / restore). Notes: `NOTES-raw.md`.
Status: decoded, disc-verified on all 722 cards, script round-trips byte-for-byte (title export->import too).

## 1. Card 2D record in WA_MRG (per card, 7 sectors)

`REC = 0x169000 + 14336*(id-1)` = in-file sector `722 + 7*(id-1)`, disc LBA `10817 + 7*id` (F125).

| part | REC offset | tool config | format |
|---|---|---|---|
| art | `+0` (`big_image_offsett_base` 0x169000) | 102x96, 256 colours, `bytes_width 102` | 8bpp, 102-byte rows, 9792 B |
| art CLUT | `+9792` (`big_image_header_offsett_base` 1488448 = 0x16B640) | 256 entries | u16 BGR555 LE, 512 B; entry 0 = `0x8000` (opaque black) on every stock card |
| title | `+10304` (`name_offsett_base` 0x16B840) | 96x14, 16 "colours", `ppb 2`, `bytes_width 48` | 4bpp, 48-byte rows, 672 B; indices 0 (transparent) and 1..7 (1 lightest .. 7 darkest) — stock titles use exactly 0..7 |
| thumb | `+10976` (`tiny_image_offsett_base` 0x16BAE0) | 40x32, 64 colours | 8bpp, 40-byte rows (1280 B) + 64-entry CLUT (128 B) at `+12256` (`tiny_image_header_offsett_base` 1490912 = 0x16BFE0) |
| pad | `+12384..14336` | | zero |

Second thumbnail copy: WA_MRG in-file sector `id-1`, i.e. `0x800*(id-1)` (`tiny_image_2_offsett_base` 0,
CLUT at `+1280` = `tiny_image_2_header_offsett_base`), followed by 640 bytes of `FF`. **Verified byte-identical
to the record copy for all 722 cards.** (So sectors 0..721 of WA_MRG are the 722 thumbnails; the card records
start at sector 722. F125's "+10976 a 16x88 8bpp strip" is this 40x32 thumbnail + CLUT — 1408 bytes either way;
the game's LoadImage rect (312,256,8,88) is just a raw 1408-byte transfer.)

Title CLUT: the tool previews titles through `name_header_offsett_base` 12075456 = 0xB83C40 (16 entries:
`8000 8001 8001 ...` — a near-black placeholder) but never writes it; the game draws titles through its own
8-grey ramp CLUT at VRAM (480,248) (F125, `psx_card_skins.c`). The site rasterises names on a canvas (16 px
font scaled to 14 rows, fill rgb(8,8,8), optional full-width squeeze / centring / padding) and maps each
pixel's inverted luminance onto a fixed 16-entry grey list `S` (0 transparent, 184,152,128,104,88,64,32 for
1..7, the rest 8-red padding), clamping the index to <= 7. "Update Name" (`serial`) re-renders all 722 titles
with the chosen font in one pass (`checkSerial`, ids 0..721).

Import quantisation (shared `ImageConverter`): 5-bit rounding per channel, histogram of the most frequent
`num_colors` colours (padded with the most frequent one), sorted by RGB, nearest-colour mapping, no
dithering; `keep_black` turns (0,0,0) into (8,8,8); transparent pixels take the first palette entry with
alpha 0. `setNewHeader` writes `STP=1` on every non-black entry (stock data has STP set on all opaque entries).
`getIncrement`: images 0/1 (art, thumb) advance by 14336 per card, image 4 (thumb copy 2) by 2048, image 3
(the frame) by 0.

## 2. Card frame texture (the card border drawn behind art and stats)

| | |
|---|---|
| WA_MRG offset | `card_offsett_base` 0xB63000 = in-file sector 0x16C6 (5830), disc LBA 15932 |
| format | 8bpp, 128-byte rows (`bytes_width 128`); the tool reads 300 rows but chunks reach row 288 |
| CLUTs | `card_header_offsett_base` 12075008 = 0xB83A80 `+ 512*k`, 256 entries each, k = `moveByType` |
| assembled canvas | 144x200 from 5 (monster) or 6 (magic/trap/ritual/equip) rectangles, see below |

Chunk maps (`ot[3]` monsters, `ot[5]` when `card.data.type > 19`), texture (x,y,w,h) -> canvas (x,y):

    monster:  (0,0,128,192)->(0,0)   (0,256,16,128)->(128,0)  (32,256,16,72)->(128,128)
              (64,272,64,8)->(0,192) (64,280,64,8)->(64,192)
    spell:    (0,0,128,128)->(0,0)   (0,192,128,64)->(0,128)  + the same four edge/bottom strips

i.e. rows 128..191 of the texture hold the monster lower body (ATK/DEF box), rows 192..255 the spell/trap
lower body, and the 144-px-wide card gets its right 16 columns from a side strip at rows 256..383.
`moveByType` = `(type-20)%3+1` for types >= 20, else `bgColor` (from the SLUS "card colour" patch, below),
else 0. Palette 0 renders the stock monster frame correctly (`scripts/` + `image-builder/scripts/raw_image.py
export ... --chunks presets/card_frame_monster.json`); palettes 2/3 look garish on this texture, so their real
consumer is unverified.

**Quirk:** 0xB63000 is the first byte of duel-overlay copy 0. `func_800179F4` (duel start) requests
`sector = 0x16C6 + 235*gDuel_bTerrain, 0xEB sectors` — 7 copies of 235 sectors, one per terrain, at
`0xB63000 + 0x75800*k`, and the frame texture + CLUTs (`0x20C80` bytes) are byte-identical in all 7. The site
writes **only copy 0**, so a frame edited with this tool shows up only in duels on terrain 0; a complete mod
must write all seven (`raw_image.py import ... --extra-body 0xBD8800 0xC4E000 0xCC3800 0xD39000 0xDAE800
0xE24000 --extra-clut <same +0x20A80>`).

The "card colour" nibble table the tool reads (`getBGCode`) is another tool's SLUS patch:
`0x800293FC` (file 0x19BFC, stock `24130100 00008021` = `li s3,0x100; move s0,zero`) -> `j 0x801DADE0;
addiu s3,a0,-1`; stub at 0x801DADE0 (file 0x1CB5E0, stock zeros) = `s3 = 0x100 + nibble(card)` from a 361-byte
table at 0x801DAE24 (file 0x1CB624; low nibble = even card index), then `j 0x80029404`. s3 is the CLUT row
index (256 + palette) the card page uses, hence `512*bgColor` here.

## 3. Description icons and text colours

- Icons for the description editor: 16x16 4bpp cells of the UI icon sheet at 0xB50000 (256x160, 128-byte
  rows; icon (t,e) = bytes x 4t..4t+8, rows 8e..8e+16, i.e. cells at pixel (8t, 8e)), palettes
  `11928064 + 32*i` = 0xB60100 + 32*i (i = 0..24, 48, 49; 24 and 48 are the two real palettes, the others are
  near-black). These are only rendered to base64 for the editor UI; nothing is written.
- `colorPointers` 0xB60F00 + 32*i (8 x 16-entry palettes) and 0xB83C40 (16 entries) are shown in the COLORS
  panel through `PalleteEditor`, which rewrites a whole 16-entry ramp from an HSL pick. **On the stock disc all
  eight 0xB60F00 palettes are zero**, so what the game does with them (if anything) is unverified.

## 4. Price / password table (WA_MRG)

| | |
|---|---|
| offset | `16488448 + 8*id` = 0xFB9800 + 8*id (id 1..722; entry 0 unused) |
| record | u32 LE price (tool clamps to 0..999,999), u32 LE password shown as 8 hex digits (`getUint8(+7..+4)`) |
| verified | id 1 Blue-eyes: 999999 / `89631139`; id 2: 160 / `15025844`; id 722: 999999 / `FFFFFFFE` |
| location | sector 0x1F73 = inside the password screen's module load (`0x1F2F + 0x56` sectors, F133); the name-entry twin block at 0xF91800 is **not** a copy |

## 5. What the game does with it

- Library / chest viewer (F125): the record is CD-DMA'd whole into `gLibrary_aCardArtRecord` (0x801DC000);
  `LoadImage` (0x8007F978) uploads art -> (256,256,51,96), CLUT -> (512,240,256,1), title -> (256,352,24,14),
  thumb bytes -> (312,256,8,88). The art sprite reads page (256,256) through CLUT (512,240); the title is 4bpp
  through the grey ramp at (480,248).
- Thumbnails (sector `id-1`): drawn in the deck/trunk lists and duel hand; the per-card single-sector layout
  lets the game fetch one sector per card without touching the 7-sector record. The reader is not in the EXE's
  literal sector list (computed `id-1`), so it is not identified here.
- Frame texture: streamed as part of the duel overlay copy for the terrain, so it is only re-read on duel
  start.
- Limits: 256 colours art, 64 colours thumb, 8-level title, 144x200 frame with fixed cut-outs.

## 6. Recomp options

- Art/title: already done natively by `src/psx_card_skins.c` (LoadImage source swap at 0x8007F978, PNG ->
  median cut, TTF title). Thumbnails would follow the same pattern once the thumb LoadImage rect/caller in the
  deck screens is measured; until then patch sector `id-1` and REC+10976 in the disc image.
- Frame: swap the source of the duel overlay's frame upload, or patch all 7 copies in the image
  (`raw_image.py` with `--extra-body/--extra-clut`).
- Price/password: data in the password module load; a frame hook after the module loads can rewrite the RAM
  copy (module base 0x80168000, table offset = 0xFB9800 - 0x1F2F*0x800 = 0x22800 -> 0x8018A800 if the module
  is loaded flat; verify live).

## 7. Decomp findings (proposed)

- WA_MRG sectors 0..721 | one sector per card: 40x32 8bpp thumbnail (1280 B) + 64-entry CLUT (128 B), `FF`
  padding; byte-identical to REC+10976 of the 7-sector record (all 722) | `WA_CardThumbs`
- REC+10976 (F125 "16x88 strip") | is the 40x32 thumbnail + CLUT above, not a 16x88 image | amend F125
- WA_MRG 0xB63000 + 0x75800*k, k = 0..6 | duel overlay copies begin with a 128-byte-wide 8bpp texture whose
  rows 0..287 are the card frame (monster body rows 0..191, spell body rows 192..255, side strips rows
  256..383 cols 0..47) with 4 x 256-entry CLUTs at +0x20A80; identical across the 7 terrain copies |
  `DuelOverlay_CardFrameTexture`
- `func_800179F4` | duel start CD request: sector `0x16C6 + 235*gDuel_bTerrain`, 0xEB sectors (the 7 x
  235-sector overlay copies live at in-file sector 0x16C6, not 0) | `Duel_LoadOverlayForTerrain`
- WA_MRG 0xFB9800 + 8*id | price u32 / password u32 table inside the password module (sector 0x1F73) |
  `gPassword_aCardPricePassword`
- `0x800293FC` / stub 0x801DADE0 / table 0x801DAE24 | the site's per-card frame-colour patch (CLUT row
  256+nibble) | (facts for the `process-cardcolor` folder)

## 8. Open questions

- Which function reads thumbnail sector `id-1`, and its VRAM rect.
- The real consumer of CLUT rows 2/3 at 0xB83A80 and of the zero palettes at 0xB60F00.
- Server side: `api/v2/userGames/getBlockData` (user block data) and `api/v2/tools` analytics only; no image
  data comes from the server.
