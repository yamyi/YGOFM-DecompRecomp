# Drop Editor tool

Route: `extend/tools/drop` (page version V.230303). Inputs: SLUS_014.11 (`.11`, used only to
read card names) and WA_MRG.MRG (`.mrg`), both through the file-tree picker, plus an `.xlsx`
(up to 20 MB) filled from the site's drop template. Client-side only; the two files are
downloaded back with `saveAs`.

Purpose: rewrites the 39 per-opponent weight blocks in WA_MRG.MRG (opponent deck pool +
the three drop tiers), reports cards that no opponent can ever drop, and optionally
"locks" the tables (obfuscates the weights and patches the SLUS so the game decodes them).

Status: decoded, disc-verified (all 156 stock tables sum to 2048), loader and consumers
disassembled, LOCK stub decoded. Script: `scripts/drop_tables.py` (dump / verify /
export / import CSV / lock / unlock / restore on WA_MRG.MRG or a raw disc image;
slus-inspect / slus-lock / slus-restore for the LOCK patch). Raw notes: `NOTES-raw.md`.

## 1. The data: 39 opponent blocks in WA_MRG.MRG

    WA_MRG.MRG offset 0xE9B000 + 0x1800 * (id - 1)      id = opponent 1..39
    in-file sector    0x1D36 + 3*(id-1)                  disc LBA 17580 + 3*(id-1)
    block = 4 rows x 1460 B (722 x u16 weight, index = card id - 1, +16 B zero pad),
            then 304 B of rank-score data (identical in every block)

| block offset | RAM (per duel) | decomp name | contents |
|---|---|---|---|
| +0x000 | 0x801781D8 | `gDuel_awOpponentDeckPool` | weights the opponent's 40-card deck is drawn from |
| +0x5B4 | 0x8017878C | `gDuel_awSaPowCardDrops` | drop tier 0: rank S/A, POW |
| +0xB68 | 0x80178D40 | `gDuel_awBcdCardDrops` | drop tier 1: rank B/C/D |
| +0x111C | 0x801792F4 | `gDuel_awSaTecCardDrops` | drop tier 2: rank S/A, TEC |
| +0x16D0 | 0x801798A8 | `gDuel_awRankScoreChange` | 304 B rank-point table, same bytes in all 39 blocks |
| +0x1800 | 0x801799D8 | `gDuel_awRitualData` | (next thing in RAM, not part of the block) |

Stock, verified on the US disc: every one of the 156 rows sums to exactly 2048. Samples
(`drop_tables.py dump`): Simon (id 1) deck pool 32 distinct cards, 343 x100; S/A-POW 9 x90,
16 x60; Duel Master K (id 39) has Simon's deck pool but his own drops (335 x36 / x48).

The site's spreadsheet layout (`createDropData`): sheet 1, one row per card at row
`card + 5` (rows 6..727), four columns per opponent starting at column C:
`column index = 4*(id-1) + n + 3` with n = 0 deck, 1 POW, 2 BCD, 3 TEC (opponent 1 = C..F,
opponent 2 = G..J, ..., opponent 39 = EY..FB). Each cell is `parseInt(v) % 65536`; an empty
or non-numeric cell is written as 0 and listed under "There are non numerical values"
(first 101 only). After import the page checks every row for a 2048 total ("In some list
the sum is not 2048") but writes the file regardless. `drop_tables.py export/import` uses a
CSV with the same information (`card,1:deck,1:pow,1:bcd,1:tec,2:deck,...`).

"MISSING CARDS" panel: cards whose weight is 0 in all 117 drop rows (tiers 1..3 of all
39 opponents; the deck pools are ignored, so are any tower/extra tables a mod might add).

## 2. LOCK: obfuscated weights + SLUS decoder stub

Only the three drop tiers are encoded (the deck pool is left alone because
`Duel_ShuffleDeck` reads it raw): `w' = 8*w + 2512 + rand(0..6)` for every one of the
722 x 117 cells (max 2048 -> 18902, fits u16; a 0 becomes 2512..2518). The SLUS then gets
two patches so `Duel_SelectCardDrop` undoes it:

| | file offset | RAM | stock | patched |
|---|---|---|---|---|
| hook | 0x12060 (8 B) | 0x80021860 | `21208200` `2A108500` = `addu a0,a0,v0` / `slt v0,a0,a1` | `F4FF0608` `00000000` = `j 0x801BFFD0` / `nop` |
| stub | 0x1B07D0 (24 B) | 0x801BFFD0 | 24 zero bytes (tail of the text bank, zero run 0x801BFB4E..0x801C0002) | see below |

    801BFFD0  2442F630  addiu v0, v0, -2512      ; v0 = lhu weight
    801BFFD4  000210C3  sra   v0, v0, 3          ; (w' - 2512) >> 3 = w  (the rand(0..6) falls out)
    801BFFD8  00822021  addu  a0, a0, v0         ; the two displaced instructions
    801BFFDC  0085102A  slt   v0, a0, a1
    801BFFE0  0800861A  j     0x80021868         ; back to the beqz
    801BFFE4  00000000  nop

Consequences: a locked WA with a stock SLUS makes every weight >= 2512, so the first
card with any weight is always dropped; a locked SLUS with plain tables decodes 0..2048
to negative numbers (`lhu` then signed subtract), the running sum never reaches the
threshold and the roll returns 0 = no drop. The site's own editor shows the encoded
values after a lock, hence "only use this option when the data is finished".

Multi-drop variant ("isGhostIso"): if the SLUS carries TEA's multi-drop process (144-byte
signature at file 0x19B3C0 / RAM 0x801AABC0, a relocated copy of the roll wrapped in a
5-iteration loop, zero in the stock EXE) the hook is written at file 0x19B434
(RAM 0x801AAC34, the relocated `addu a0,a0,v0`) and additionally into WA_MRG at
`0xBC1CB4 + k*0x75800`, k = 0..6 (stock bytes there are data, `1A 00 44 00 02 00 80 14`),
and the stub's return jump becomes `j 0x801AACBC`. 0x801AABC0 lies inside the duel
overlay's arena (0x80146000..0x801BB800), which is why that variant has to be re-applied
inside seven WA_MRG copies. Details in `NOTES-raw.md`; the multi-drop process itself
belongs to another tool.

## 3. What the game does with it

Load (duel bootstrap `func_800179F4`, 0x80017AB0..0x80017AEC):

    80017AB4  lb   v0, gDuel_bOpponentID          ; 0x8009B361, id 1..39
    80017AC0  sllv a2, v0, s0   (s0 = 1)
    80017ACC  addu a2, a2, v0                     ; a2 = 3*id
    80017AD0  addiu a2, a2, 0x1D33                ; sector = 0x1D33 + 3*id
    80017AD4  li   a3, 3                          ; 3 sectors = 0x1800 bytes
    80017AD8  la   v0, gDuel_awOpponentDeckPool   ; dest 0x801781D8 (sp+0x18)
    80017AE8  jal  func_80014E1C(0, 0, sector, 3, 0, 0, dest)

So the block for the current opponent is streamed straight over 0x801781D8 at the start of
every duel; the EXE image holds zeros there.

Deck: `Duel_ShuffleDeck` (0x800243F4, a0 == 0) draws 40 cards from the pool with the
usual walk — threshold `(rand() & 0x7FF) + 1`, running sum over entries 0..719 (not 722),
at most 3 copies per card, a refused 4th copy is redrawn.

Drop tier choice, in `Duel_MaybeEndOfDuel` (0x800218F0) at 0x80021BE8..0x80021C84, gated
by `D_8009B360 >= 0`, `gDuel_bOpponentID >= 0` and `gp+0x25D == 0` (the human side won):

    80021C2C  lbu v0, 0x38(duel)      ; rank index 0=D 1=C 2=B 3=A 4=S
    80021C38  sb  v0+1, 0x3A(duel)    ; starchip prize = rank + 1
    80021C44  lbu v0, 0x39(duel)      ; nonzero = TECHNIQUE
    80021C48  lbu v1, 0x38(duel)
    80021C4C  v0 = (tec != 0);  v1 = (rank < 3)
    80021C58  a0 = tec << 1           ; 0 = S/A POW, 2 = S/A TEC
    80021C5C  if rank < 3: a0 = 1     ; B/C/D
    80021C60  jal Duel_SelectCardDrop
    80021C74  sh  v0, gDuel_wSelectedCardID ; 0x8009B338
    80021C78  sh  v0, 0x3C(duel)            ; D_8009B1E8 + 0x3C
    80021C84  sw  v0, gDuel_CardDropID2     ; 0x801D56A8

`Duel_SelectCardDrop` (0x80021810, matched C in `src/weighted_random_pick.c`): row =
`gDuel_awSaPowCardDrops + 1460*a0`, one `rand()`, threshold 1..2048, walk all 722 weights,
return index+1 or 0. The card is banked later at 0x80021F14 by `ring_buffer_insert_801d0200`
(0x80021894, trunk + 1 and the 16-slot recent list). Consequences: a row under 2048 can
miss (0 = no card), a row over 2048 makes everything after the crossing point
unreachable, id 721/722 are drawable here (unlike the deck walk).

## 4. Recomp options

The recomp already has this capability natively: `src/psx_drop_edits.c` (INI of complete
per-duelist weight vectors) and `src/psx_drop_missing.c` rewrite the resident tables at
0x801781D8 after the duel load, guarded by a fingerprint of the four rows. Two things from
this tool improve them:

1. Opponent identity without fingerprints: the id is `gDuel_bOpponentID` (`lb` 0x8009B361)
   and the table on disc is at LBA `17580 + 3*(id-1)`, so a mod can key edits by id and
   also read the stock rows straight off the disc image instead of baking them.
2. Locked discs: if a player's SLUS has `psx_mod_read_word(0x80021860) == 0x0806FFF4`
   the resident weights are encoded; decode with `(w - 2512) >> 3` before displaying or
   editing, and re-encode when writing back (or leave the tables alone and hook
   `Duel_SelectCardDrop` natively so the encoding is irrelevant).

The LOCK stub itself has no place in the recomp: 0x801BFF80.. is also where
`psx_card_shop.c` parks its replacement glyph stream, so the two would collide.

Full editor as a mod: frame hook; when `psx_mod_read_word(0x801798A8) == 0x000C0005`
(first word of the rank table, present as soon as the block has landed) and the rows are
still stock (compare against the disc rows for `gDuel_bOpponentID`), write the player's
156 rows with plain data writes. Re-check every frame because the block is reloaded per
duel. Weight rows must still total 2048 unless the roll is also replaced.

## 5. Decomp findings (proposed)

- 0x80017AB0..0x80017AEC | duel bootstrap streams WA_MRG sector `0x1D33 + 3*gDuel_bOpponentID` (3 sectors) to 0x801781D8: deck pool, three drop tiers, rank table | `Duel_LoadOpponentTables` (call site), block layout above
- 0x801798A8 | 304 B trailer of every opponent block, identical for all 39 | confirms `gDuel_awRankScoreChange` is disc data, not per-opponent
- 0x80021C2C..0x80021C5C | tier = rank<3 ? 1 : (tec ? 2 : 0); duel object +0x38 rank index (0=D..4=S), +0x39 TEC flag, +0x3A prize = rank+1, +0x3C drop id | field names for `D_8009B1E8`
- 0x800243F4 | `Duel_ShuffleDeck(a0=0)` draws the opponent deck from `gDuel_awOpponentDeckPool`: 40 draws, 720-entry walk, 3-copy cap | keep name, add description
- 0x801BFB4E..0x801C0002 | zero tail of the text bank; the site's LOCK stub lives at 0x801BFFD0 | unused arena (shared with the recomp card shop at 0x801BFF80)

## 6. Open questions

- The page says "In this link you will find the excel file with the template" but the
  chunk contains no template URL (only the `.xlsx` accept filter); the template is
  probably shared with `data/dropUI`. The CSV produced by `drop_tables.py export` carries
  the same cells.
- The multi-drop variant's WA offsets (`0xBC1CB4 + k*0x75800`) and its return address
  0x801AACBC (0x80 past the relocated compare) could not be checked without a multi-drop
  SLUS/WA pair.
- Dead code in the chunk: `getMusic`/`setMusic` at SLUS offset 87496 (0x155C8) are
  leftovers from another tool and never called here.
- Server side: `POST api/v2/tools` only logs the download; nothing else is remote.
