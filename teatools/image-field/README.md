# FIELD tool (duel floor textures, terrain bonus table, field-name banner)

Route: `extend/tools/image/field` (V.220608). Inputs: SLUS_014.11 (`.11`,
1,782,579..2,097,152 bytes) and WA_MRG.MRG (`.mrg`, 36,700,160..39,845,888 bytes), plus
PNG/BMP images (16 colours): 256x104 for the top and bottom halves of a floor, 256x46 for the
middle band, and a 56x144 "Image Name" template. Three tabs: IMAGES, Bonus Value, NAMES.
Client-side; both files are downloaded back.
Script: `scripts/field_tex.py` (inspect / export / import / restore / verify textures;
boost / set-boost / restore-boost; export-atlas / import-atlas). Raw notes: `NOTES-raw.md`.
Status: textures and bonus table decoded and disc-verified (renders: arena = yellow stone,
Forest = green tiles), round trips and byte-identical restores tested on copies; the banner
atlas is mapped from the site's chunk table only. Not yet built as a mod.

## 1. Floor textures (WA_MRG.MRG)

The duel overlay (the code/data block mapped at 0x80146000) exists on the disc in **seven
copies, one per terrain**, and the copy is chosen by the field:

```c
/* src/register_handler_800171A8.c -- func_8001798C */
scaled = D_8009B364 * 235 + 0x16C6;            /* gDuel_bTerrain: 0 arena, 1 Forest .. 6 Yami */
func_80014E1C(0, 0, scaled, 0xEB, select_sound_preset, 0, 0);   /* 235-sector stream */
```

Copies are byte-identical in sectors 0..202 and differ only in sectors 203..218 (the floor
texture) and 222, 226, 230, 232 (four single sectors, not decoded). Texture of terrain t:

    WA offset = 0xBC8800 + t * 0x75800     in-file sector 0x1791 + 235*t     disc LBA 16135 + 235*t
    t: 0 arena 0xBC8800 | 1 Forest 0xC3E000 | 2 Wasteland 0xCB3800 | 3 Mountain 0xD29000
       4 Sogen 0xD9E800 | 5 Umi 0xE14000 | 6 Yami 0xE89800        (site: body 0xBC8800 + 481280*fieldID)

| in-texture | content |
|---|---|
| rows 0..103 (128 B each) | top half, 4bpp, 256 px wide (low nibble = left pixel) |
| rows 104..207 | bottom half |
| rows 208..253 | middle band (46 rows; the site shows 45 and repeats it rotated 180 degrees) |
| +0x7F00 (rows 254..255) | 8 CLUT slots x 16 entries x 2 B: slots 0,1 = top, 2,3 = bottom, 4 = middle, 5..7 zero (site: header 12388096 = body + 0x7F00, `duplicates` [0,32] / [64,96] / [128]) |

Stock CLUTs have no STP bits and no zero entries (opaque floor). The five slots differ from
one another in every stock copy (the pairs are not duplicates in stock data; the site writes
the same palette to both slots of a pair). The 16 sectors are one 4bpp texture page column
(64 halfwords x 256 rows) with its CLUTs in the last two rows.

## 2. Terrain power bonus (SLUS_014.11)

| | |
|---|---|
| file offset | 0x811D4 (site: 528852), 120 bytes |
| RAM | 0x800909D4 = `gDuel_aTerrainBoost`, `s8[20 types][6 terrains]`, value x 10 |
| reader | `Duel_GetTerrainBoost` 0x8002497C: `if (gDuel_bTerrain == 0 \|\| type >= 20) return 0; return table[type*6 + terrain - 1] * 10` |

    800249A4  addiu a0, a0, 0x9D4        ; &gDuel_aTerrainBoost (a0 = 0x80090000)
    800249A8  sll   v0, v1, 1 ; addu v0, v0, v1 ; sll v0, v0, 1     ; type*6
    800249BC  addiu v0, v0, -1 ; addu v1, gDuel_bTerrain, v0 ; addu v1, v1, a0
    800249C8  lb    v1, 0(v1)
    800249D0  sll v0, v1, 2 ; addu v0, v0, v1 ; sll v0, v0, 1       ; *10

Stock table (columns Forest, Wasteland, Mountain, Sogen, Umi, Yami; types in the order of
global strings 768..787): Dragon +500 Mountain; Spellcaster +500 Yami; Zombie +500 Wasteland;
Warrior +500 Sogen; Beast-Warrior +500 Forest and Sogen; Beast +500 Forest; Winged Beast +500
Mountain; Fiend +500 Yami; Fairy -500 Yami; Insect +500 Forest; Dinosaur +500 Wasteland;
Reptile none; Fish +500 Umi; Sea Serpent +500 Umi; Machine -500 Umi; Thunder +500 Mountain
and Umi; Aqua +500 Umi; Pyro -500 Umi; Rock +500 Wasteland; Plant +500 Forest.
The site edits each cell in steps of 10 within -1280..1270 (the s8 range).

## 3. "Image Name" banner atlas (WA_MRG.MRG)

The NAMES tab edits a 56x144 (canvas 56x168) 16-colour picture that the page assembles from
46 pieces of a 4bpp atlas at WA 0xB51000 (sector 0x16A2, 36 sectors before the overlay
copies; CLUT of 16 greys, entry 0 transparent, at 0xB609A0). The atlas is the in-duel UI sheet
(FIELD / MEADOW / WASTELAND / MOUNTAIN / FOREST / SEA / DARK fragments, frame pieces, CAUTION!,
arrows -- see `export-atlas`). The piece table is transcribed into `field_tex.py`
(`ATLAS_CHUNKS`); several canvas rows map to the same atlas piece (borders), so an import
writes each shared piece from the last canvas row that references it, exactly like the site.
Which load brings this sheet into VRAM was not traced.

## 4. Recomp options

- Bonus table: base-EXE data. One `psx_mod_write_byte(0x800909D4 + type*6 + terrain-1, v/10)`
  per changed cell at startup (check the stock byte first). A native mod could hook
  `Duel_GetTerrainBoost` (0x8002497C) instead and compute anything (e.g. per-card bonuses).
- Floor textures, disc-level: `field_tex.py import` on WA_MRG.MRG in the .bin.
- Floor textures, runtime: the 16 texture sectors stream through the overlay load's callback
  (`select_sound_preset` 0x800171A8 -- still an asm stub in the decomp, so the VRAM rect is not
  known; measure it with the debug server's vram_peek during a duel start) and can be swapped
  with the `LoadImage`-stub idiom, or re-uploaded after the duel overlay finishes loading
  (keyed on `gDuel_bTerrain`).

## 5. Decomp findings (proposed)

- WA sector 0x16C6 + 235*t | seven terrain-specific copies of the 235-sector duel overlay; sectors 0..202 identical, 203..218 = 4bpp floor texture (rows 0..253 + CLUT slots at +0x7F00), 222/226/230/232 terrain-specific single sectors | (disc fact)
- `0x8001798C` | loads the overlay copy for `gDuel_bTerrain` (235 sectors from 0x16C6 + t*235) | `Duel_LoadOverlayForTerrain`
- `0x800171A8` (`select_sound_preset`) | is the overlay stream callback registered by that load, not a sound routine (name is wrong; the SPU-preset reading came from the same obj-mode-dispatch shape) | `Duel_OverlayStreamCb` (needs the asm read)
- `gDuel_aTerrainBoost` | layout confirmed: `s8[20][6]`, x10, terrain columns 1..6 = Forest, Wasteland, Mountain, Sogen, Umi, Yami; type rows = global-bank strings 768..787 | (fact)
- WA 0xB51000 | 4bpp duel UI atlas (field-name words, frames, CAUTION!) with a 16-grey CLUT at 0xB609A0 | (disc fact)

## 6. Open questions

- VRAM destination of the floor texture and the four other terrain-specific sectors.
- The atlas load and its VRAM position; the page's 56x144 template image
  (`/Assets/img/templates/field03.png`) and the seven preview thumbnails
  (`/Assets/img/field/field-0N.png`) redirect to the login page, so they could not be mirrored.
- A dead code path in the page (`index == 3`, `parts2`) reads the same atlas with a 15-piece
  map; it is not reachable from the UI.
