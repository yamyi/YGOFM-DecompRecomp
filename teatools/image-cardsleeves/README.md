# Card Sleeves tool (big card face + card back)

Route: `extend/tools/image/cardsleeves` (page version V.220722). Inputs: **WA_MRG.MRG**
(`.mrg`, 36,700,160..39,845,888 bytes), **SLUS_014.11** (`.11`, 1,782,579..2,097,152 bytes)
and PNG/any browser image (`image/*`, up to 20 MB). Everything is client-side; the only
server traffic is the analytics POST `api/v2/tools` (tipo 20) and `userGames/getBlockData`.
Purpose: replace the big-card frame that every card is drawn on (a "dynamic" layer that is
recoloured per card colour, plus a "static" overlay), replace the card back ("sleeve"),
move the six elements the game draws on top of the frame (art, title, ATK, DEF, stars,
attribute), and wipe the baked "[Normal Magic Card] / ATK / DFD" 4bpp placeholders.
Status: decoded, disc-verified, loader + VRAM map traced, offline clone written,
not yet built as a recomp mod.

Script: `scripts/card_sleeves.py` (dump / verify / apply / restore on a WA_MRG copy, and
`positions` for the SLUS bytes; `dump`/`verify` also read a MODE2/2352 .bin directly).
Templates and examples shipped by the site: `site/Assets/img/templates/bigcard.zip`
(144x264 "big card dynamic/static part" and 144x200 "sleeve" templates + 3 example sets).
Raw notes: `NOTES-raw.md`.

## 1. Where the card texture lives: ten copies in WA_MRG.MRG

The tool writes every change to 10 places ("cicles" in the JS: `0, 481280, 962560,
1443840, 1925120, 2406400, 2887680, 3684352, 4409344, 5658624`). They are the graphics
bundles of the screens that draw big cards. Each bundle starts with the same 128 KB
texture block and carries a 16-row CLUT block a little later:

| copy | texture block @ WA_MRG | in-file sector | disc LBA | CLUT block @ | loaded by (`func_80014E1C(0,0,sector,count,callback)`) |
|---|---|---|---|---|---|
| duel arena k = 0..6 | `0xB63000 + 0x75800*k` | `5830 + 235*k` (0x16C6) | 15932 + 235k | `0xB83000 + 0x75800*k` | `func_8001798C`: sector `0x16C6 + 235*gDuel_bTerrain`, 0xEB sectors, cb `0x800171A8` (misnamed `select_sound_preset`) |
| library / build deck | `0xEE6800` | 7629 (0x1DCD) | 17731 | `0xF06800` | `func_8002BFCC` (from `Main_RunLibraryMenu`): 0x8A sectors, cb `func_8002BD0C` |
| password screen | `0xF97800` | 7983 (0x1F2F) | 18085 | `0xFB7800` | `register_handler_8003BD14`: 0x56 sectors, cb `func_8003BD14` |
| bundle 0x2189 | `0x10C4800` | 8585 (0x2189) | 18687 | `0x10E8800` | `call_14e1c_137e4` (0x8003232C, called from `spawn_fade_teardown_dispatch` / `func_800323F8`): 0x4C sectors, cb `func_80032184` |

The tool's `body_offset` 0xB63000 / `pallete_offset` 0xB84000 (+512 per colour) plus the
cycle offsets give exactly these addresses; the last cycle subtracts 0x4000 from the body
because the 0x2189 bundle inserts an 8-sector (832,0) upload between the texture and the
CLUT block (see section 3), so its CLUT block is at +0x24000 instead of +0x20000.

Stock content, verified on the US disc: the first 592 rows (face, sleeve, edges) and CLUT
rows 8 and 10..15 are byte-identical in all ten copies (md5 of rows 0..592 of copy 0:
`1b8ac4232e416745719428b2b1695402`). The password and 0x2189 copies differ from row 592 on
(they carry no mini cards) and in CLUT rows 0..7 / row 9. `card_sleeves.py verify` prints
this table.

### The texture block: 0x20000 bytes = 1024 rows of 128 bytes

The block is a raw VRAM column: 128 bytes = 64 VRAM halfwords per row, streamed one 2 KB
sector (16 rows) at a time. Row `r` lands at VRAM `x = 768 + 64*(r/256)`,
`y = 256 + r%256` (halfword coordinates), i.e. four texture pages (768,256), (832,256),
(896,256), (960,256). In 8bpp texel units a page is 128 wide.

| rows | bytes | content (8bpp unless noted) | VRAM (page, u, v) |
|---|---|---|---|
| 0..192 | 0..128 | big-card face, main body 128x192 | page (768,256) u0..127 v0..191 |
| 192..256 | 0..128 | face lower box 128x64 (canvas rows 200..264 of the 144x264 template) | (768,256) v192..255 |
| 256..384 | 0..16 | face right edge 16x128 (canvas x128..143) | (832,256) u0..15 v0..127 |
| 256..384 | 16..32 | sleeve right edge 16x128 | (832,256) u16..31 |
| 256..328 | 32..48 / 48..64 | face / sleeve right edge, lower 72 rows | (832,256) u32..63 |
| 256..272 | 64..128 | sleeve bottom strips 2 x 64x8 (canvas y192..199) | (832,256) v0..15 |
| 272..288 | 64..128 | face bottom strips 2 x 64x8 | (832,256) v16..31 |
| 384..576 | 0..128 | card back ("sleeve") 128x192 | (832,256) v128..255 + (896,256) v0..63 |
| 592..768 | 0..128 | mini-card text strip + 4 mini cards 56x64 (see `../image-minicardsleeves`) | (896,256) v80..255 |
| 768..928 | 0..128 | other duel sprites (digits, MAGIC/EQUIP/TRAP/RITUAL labels, icons) | (960,256) v0..159 |
| 928..1008 | 0..28 | **4bpp** text placeholders "[Normal Magic Card]" "[Trap Card]" "[Equip Magic Card]" "ATK" "DFD", 5 strips of 16 rows | (960,256) 4bpp u0..55 v160..239 |

Tool chunk tables (`chunk-common` module `5457`): `cardTransform1` (write map for the
144x264 face) = rows 0..192 -> canvas (0,0); (0..16, 256..384) -> (128,0);
(32..48, 256..328) -> (128,128); (64..128, 272..280) -> (0,192); (64..128, 280..288) ->
(64,192); (0..128, 192..256) -> (0,200). `cardBg3` (sleeve 144x200) = rows 384..576 ->
(0,0); (16..32, 256..384) -> (128,0); (48..64, 256..328) -> (128,128); (64..128, 256..264)
-> (0,192); (64..128, 264..272) -> (64,192). `cardTransform2` (placeholder view, 60x80,
2 px per byte) = rows 928..1008 in 16-row strips, bytes 0..28 (three strips) / 0..12 (two).

### The CLUT block: 16 rows x 256 colours (8 KB), uploaded to VRAM (256,240) 256x16

Row `j` of the block is VRAM row `240 + j`, colour `i` is at `x = 256 + i`.

| block row | VRAM y | use |
|---|---|---|
| 1..7 | 241..247 | mini-card palettes (indices 64..127), see minicardsleeves |
| 8 + k, k = 0..5 | 248..253 | big-card palette for card colour k (tool colour buttons 1..6) |
| 14 | 254 | tool's "extra colour" (7th) |
| 8, colours 224..239 | (480,248) | 8-grey ramp for the baked card TITLE (F125) |
| 8, colours 240..255 | (496,248) | 4bpp text placeholder palette |

Index map inside a big-card row (what the tool calls `move`):

    0..71    dynamic face  (72 colours, recoloured per card colour)
    72..111  static face, part A (first 40 colours)
    112..159 sleeve (48 colours)
    160..191 static face, part B (remaining 32 colours; pixel index e>=40 is stored as e+48)
    224..239 title ramp   240..255 placeholder text

Colour encoding (`setNewHeader`): 15-bit BGR, `lo = (g>>3&7)<<5 | r>>3`,
`hi = STP<<7 | (b>>3)<<2 | g>>6`; STP is set for every non-transparent colour; opaque
black becomes (8,8,8) so it does not read as transparent; a fully transparent pixel maps to
colour 0x0000. `ImageConverter` quantises by rounding RGB to 5 bits, keeps the N most
frequent colours (N = 72 / 72 / 48), sorts them by RGB and maps every pixel to the nearest.

### What the tool writes (`salvarEnImagen`)

For every one of the 10 copies: the layer's palette into CLUT rows 8..13 (and 14 if
"Show Extra color?" is on) at the layer's index base, then the pixel indices through the
chunk table. Dynamic writes every canvas pixel; static writes only pixels whose colour is
opaque (an overlay); sleeve writes every pixel. The palette editor then edits each of the
seven CLUT rows separately (the shipped `configuration.txt` gives hue shifts per colour:
Normal 0, Green +74, Pink +257, Blue +190, Purple +233, Orange +317).
"Clean texts" (`cleanImage`) zeroes 10240 bytes at `0xB80000 + cycle` (rows 928..1008,
minus 0x4000 in the last copy) in all ten copies.

## 2. SLUS_014.11: where the six elements are drawn on the big card

The POSITION tab reads/writes 12 single bytes of SLUS_014.11; they are the low bytes of
`addiu` immediates inside `func_80028B08` (proposed `Card_DrawBigCard`), which builds the
sprite primitives for a big card at frame origin (`obj+0x30`, `obj+0x32`). Stock bytes
verified on `SLUS_014.11`:

| element | X: file off / RAM / word | Y: file off / RAM / word | stock | size / notes |
|---|---|---|---|---|
| image (card art) | 0x19434 / 0x80028C34 / `24420013` | 0x1944C / 0x80028C4C / `24630032` | 19, 50 | 102x96 (`0x66`,`0x60`), CLUT from obj+0xC |
| text (title) | 0x194C8 / 0x80028CC8 / `2442000C` | 0x194FC / 0x80028CFC / `2508000E` | 12, 14 | 96x14, tpage 0x1E0, 4bpp |
| atk | 0x196B0 / 0x80028EB0 / `24420061` | 0x196C4 / 0x80028EC4 / `2442009D` | 97, 157 | 4 digits, 6 px apart, glyph 6x13 (`0xD0006`) |
| def | 0x1973C / 0x80028F3C / `24420061` | 0x19750 / 0x80028F50 / `244200AB` | 97, 171 | same |
| st (level stars) | 0x197CC / 0x80028FCC / `24420077` | 0x197F0 / 0x80028FF0 / `24630020` | 119, 32 | 9x9 each, `level` copies stepping x -= 9 |
| attr (attribute) | 0x19884 / 0x80029084 / `2442006E` | 0x19898 / 0x80029098 / `2442000D` | 110, 13 | 16x16, u = attribute*16 |

    80028C2C  lhu  v0, 0x30(s2)        ; frame x
    80028C34  addiu v0, v0, 0x13       ; <-- image.x
    80028C38  sh   v0, 0x4(s1)         ; prim.x
    80028C3C  lhu  v1, 0x32(s2)        ; frame y
    80028C40  li   v0, 0x66  ; sh 0x8(s1)   w = 102
    80028C48  sh   s0(0x60), 0xA(s1)   ; h = 96
    80028C4C  addiu v1, v1, 0x32       ; <-- image.y
    ...
    80028E34  lh v0,0x32(s3); lh v1,0x36(s3); addu ; min(.., 9999) -> int_to_digits(4)  ; ATK + bonus
    80028EB0  addiu v0, v0, 0x61 ; 80028EC4 addiu v0, v0, 0x9D                         ; ATK x,y
    80028FCC  addiu v0, v0, 0x77 ; 80028FF0 addiu v1, v1, 0x20 ; loop lbu 0x3A(s3) times ; stars
    80029084  addiu v0, v0, 0x6E ; 80029098 addiu v0, v0, 0xD  ; lbu 0x3B(s3) << 4 -> u  ; attribute

Card record `D_800EA0E8 + 0x40*slot`: +0x32/+0x34 ATK/DEF, +0x36/+0x38 bonuses, +0x3A level,
+0x3B attribute, +0x3C flags (0x80 / 0x40 select the alternate digit colour 0xF9). The tool
clamps x to 0..140 and y to 0..196; the immediate is 16-bit sign-extended, so any byte
0..255 is a positive offset. This is base-EXE code, so the change applies to every screen
that draws a big card (duel, library, chest viewer, password result).

## 3. What the game does with it: the bundle loader

`func_80014E1C` -> `func_80013998` arms the shared loader object `D_800E9E60`
(sector = `gFile_anLba[file] + start`, count) and the per-frame pump
(`func_80014A5C` -> `func_8001455C` -> `func_80013C28`) reads sectors. Each time the
current transfer (`obj+0x1C` bytes) is exhausted the stage callback is called with
`(obj, stage++)` and it programs the next transfer:

* `obj+0x46 = 1`: copy sectors to RAM at `obj+0x8` (advances 0x800 per sector);
* `obj+0x46 = 2`: **stream to VRAM**: every sector goes through the 2 KB staging buffer
  `D_8009B118` and `LoadImage2(rect{x=obj+0x30, y=obj+0x32, w=64, h=16})`; then
  `y += 16`, and when `y & 0xFF == 0` (page bottom) `y` returns to the page top and
  `x += 64` (`func_80013C28`, 0x80013EC8..0x80013EFC). That is why every image in these
  bundles is a 128-byte-wide column with 256-row pages.

Duel bundle (`0x800171A8`, jump table `0x800100C0`, 13 stages, 235 sectors total):

| stage | bundle sectors | bytes | destination |
|---|---|---|---|
| 0 | 0..63 | 0x20000 | VRAM (768,256) column = 4 pages: **the card texture** |
| 1 | 64..67 | 0x2000 | staging |
| 2 | - | - | `LoadImage2((256,240,256,16), staging)` = **CLUT block**; then 5 sectors -> `equipTable` |
| 3 | 73..104 | 0x10000 | `fusionTable` |
| 4 | 105 | 0x800 | `ritualData` |
| 5 | 106..107 | 0x1000 | staging |
| 6 | - | - | `LoadImage2((0,240,256,8), staging)`; then 32 sectors -> VRAM (512,256) 2 pages |
| 7 | 140..183 | 0x16000 | RAM `*(0x800101DC)` = **0x80146000, the duel overlay code** (so it sits at in-file sector 5970 + 235k) |
| 8 | 184..186 | 0x1800 | `handAiScript` |
| 9 | 187..189 | 0x1800 | `D_801A9800` |
| 10 | 190..197 | 0x4000 | VRAM (832,0) 128 rows (micro cards, icons) |
| 11 | 198..202 | 0x2800 | RAM `0x80100000` (load arena 0) |
| 12 | 203..234 | 0x10000 | VRAM (640,256) 2 pages |

Library bundle (`func_8002BD0C`, 138 sectors): 64 -> (768,256); 4 -> CLUT (256,240,256,16);
48 -> (576,256); 1 sector -> `LoadImage2((256,246,256,2))` (overwrites CLUT rows 246/247);
20 sectors in mode 3 (0xA000); 1 sector -> `func_80048D08`. Password bundle (`func_8003BD14`,
86 sectors): 64 -> (768,256); 4 -> CLUT block; 3 -> `handAiScript`; 15 -> `*(0x800101D8)` =
0x80168000 (screen module). 0x2189 bundle (`func_80032184`, 76 sectors): 64 -> (768,256);
8 -> (832,0); 4 -> CLUT block. In every case the card texture is the first 64 sectors and
lands on pages (768..1024, 256..512), and the CLUT block goes to (256,240).

Consequences: there is no RAM-resident copy of the texture; it exists only on disc and in
VRAM. Colour k of a card is a CLUT row (VRAM y 248+k), which is why one frame image can be
recoloured per card type, and why the tool insists the dynamic part be loaded before the
static one (the static overlay indices 72..111/160..191 are shared by all rows).

## 4. Recomp options

1. **Positions (base EXE).** Twelve code bytes: `psx_mod_write_code_word` once at startup,
   e.g. image at (30,30) = `0x80028C34 <- 0x2442001E`, `0x80028C4C <- 0x2463001E` (keep the
   upper 24 bits of each stock word, replace the low byte). Cheap, no frame hook needed.
2. **Textures at the VRAM level (native replacement, recommended).** Reuse the card-skin idiom
   (`psx_card_skins.c`): redirect `LoadImage2` (0x80081DE8) or the pump's call at
   0x80013E88 through a stub; when the rect is `(256,240,256,16)` (the CLUT upload that ends
   every card-texture load) the four pages at (768..1024, 256..512) are complete, so upload
   the mod's own face/sleeve pages and CLUT rows from a host-filled buffer. One PNG each for
   dynamic (144x264), static (144x264) and sleeve (144x200), quantised by the host exactly as
   `card_sleeves.py apply` does; write rows 248..253 with the six recolours.
3. **Disc-level.** Feed patched sectors: hook the staging path (`CdGetSector` at 0x80013CCC /
   0x80013DF8) and substitute contents when the read LBA is inside one of the ten texture
   blocks (LBAs in the table above). This reproduces the site's patch bit-for-bit but costs
   a compare on every sector read.
4. **Clean texts** = zero rows 928..1008 of page (960,256): a 4bpp `LoadImage` of zeros over
   rect (960, 416, 14, 80) after the CLUT upload, or skip it entirely by moving the title/ATK
   labels with option 1.

## 5. Decomp findings (proposed)

* `0x8001798C` | duel graphics load: `func_80014E1C(0,0,0x16C6 + 235*gDuel_bTerrain, 0xEB, 0x800171A8)`; the 235-sector arena bundles start at WA_MRG sector 5830 (LBA 15932) | `Duel_RequestArenaBundle`
* `0x800171A8` (`select_sound_preset`, misnamed) | 13-stage callback of the arena bundle, table at 0x800100C0; stage 7 copies 0x16000 B to `*(0x800101DC)` = 0x80146000 = the duel overlay (bundle sectors 140..183) | `Duel_ArenaBundleStage`
* `0x80013C28` | per-sector pump: mode 2 = `LoadImage2` of a 64x16 rect at (obj+0x30, obj+0x32), then y += 16, wrap at page bottom -> x += 64; mode 1 = RAM copy | `File_PumpSector`
* `D_800E9E60` | the loader object: +0x1C bytes left, +0x30/+0x32 VRAM cursor, +0x46 mode, +0x47 stage | `gFile_Loader`
* `0x800101D8` / `0x800101DC` | load-destination words: 0x80168000 (screen modules), 0x80146000 (duel overlay) | `gMain_pModuleBase` / `gMain_pDuelOverlayBase`
* `0x80028B08` | draws a big card from a card record (`D_800EA0E8 + 0x40*slot`): art 102x96 at +(19,50), title 96x14 at +(12,14), ATK/DEF 4 digits at +(97,157)/(97,171), stars 9x9 from +(119,32) stepping -9, attribute 16x16 at +(110,13) with u = attr*16 | `Card_DrawBigCard`
* WA_MRG `0xB63000` (+0x75800k), `0xEE6800`, `0xF97800`, `0x10C4800` | card texture column, 0x20000 B -> VRAM (768,256) 4 pages; CLUT block +0x20000 (+0x24000 in the 0x2189 bundle) -> (256,240) 256x16; big-card palettes rows 248..254, title ramp (480,248), placeholder CLUT (496,248) | (facts)
* `0x8002BFCC` | it is the library/build-deck screen init (`Main_RunLibraryMenu` calls it), not a "duel select" init; requests bundle 0x1DCD x 0x8A | `Library_Init`

## 6. Open questions

* Which code picks the CLUT row (card colour) for a given card: the object field +0x5C
  that `func_80028B08` stores into the prim's CLUT slot is filled elsewhere (not traced).
* Rows 576..592 and 768..928 of the texture were not identified sprite by sprite.
* CLUT row 9 (colour 1) and rows 0..7 differ in the password and 0x2189 copies; row 15
  is unaccounted for.
* Which screen the 0x2189 bundle belongs to (callers `spawn_fade_teardown_dispatch`,
  `func_800323F8`); it draws big cards plus a (832,0) strip.
* The INFO tab's illustration `/Assets/img/capas.png` and the character templates redirect
  (302) to the site root without a session, so they are not mirrored.
* Nothing is done server-side beyond analytics.
