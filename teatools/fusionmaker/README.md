# FUSION MAKER tool

Route: `extend/tools/fusionmaker` (site version string V.260629). Inputs: SLUS_014.11 (`.11`,
1,572,864..3,145,728 bytes; read only, for card names/stats/descriptions) and WA_MRG.MRG
(`.mrg`, 36,700,160..45,088,768 bytes; the file that gets edited), optionally an .xlsx made from
`site/Assets/files/FusionTemplate.xlsx` (columns CARD 1, CARD 2, FUSION). Client-side only; the
result is the whole WA_MRG.MRG downloaded back under its original name.

Purpose: edit the game's **fusion table** - the packed "card A + card B = card C" list that
the duel engine consults for every two-card summon (player and AI). The site decodes it into a
per-card DataSet, lets you add/remove single fusions, generate whole batches (every card
matching filter set 1 x every card matching filter set 2 -> one result), import from Excel,
shows the accidental "glitch fusions" the format produces, and re-packs the table into one or
all seven per-terrain copies.

Status: format fully decoded and proved against the game's loader + lookup code; disc-verified;
offline clone in `scripts/fusion_table.py` (dump / export / import / verify / lookup / restore,
restore and import both reproduce the stock bytes exactly). **The site's file offset is one
sector (0x800) later than where the stock US disc keeps the table** - see section 2. Not yet
built as a recomp mod. Raw notes: `NOTES-raw.md`.

## 1. Where the table lives

The fusion table is not in the EXE. It is part of the **per-terrain duel data block** in
WA_MRG.MRG that `Main_RunDuel` streams in at the start of every duel:

    block(t) = in-file sector 0x16C6 + 235*t   (t = gDuel_bTerrain, 0..6), 235 sectors = 0x75800 bytes
             = WA_MRG offset 0xB63000 + t*0x75800      disc LBA 15932 + 235*t
    fusion table = block + 0x24800, exactly 0x10000 bytes  ->  RAM 0x8017C2D8 (gDuel_aFusionTable)

| terrain t | site name | WA_MRG offset (game) | in-file sector | disc LBA | site's offset |
|---|---|---|---|---|---|
| 0 | Normal    | 0xB87800 | 0x170F | 16005 | 0xB88000 |
| 1 | Forest    | 0xBFD000 | 0x17FA | 16240 | 0xBFD800 |
| 2 | Wasteland ("Watesland" on the site) | 0xC72800 | 0x18E5 | 16475 | 0xC73000 |
| 3 | Mountain  | 0xCE8000 | 0x19D0 | 16710 | 0xCE8800 |
| 4 | Meadow    | 0xD5D800 | 0x1ABB | 16945 | 0xD5E000 |
| 5 | Sea       | 0xDD3000 | 0x1BA6 | 17180 | 0xDD3800 |
| 6 | Dark      | 0xE48800 | 0x1C91 | 17415 | 0xE49000 |

All seven stock copies are byte-identical (the seven blocks differ only in 20 sectors of terrain
graphics at block+0x65800..+0x6F800). Stock bytes (terrain 0, verified on the US disc):

| what | offset | bytes |
|---|---|---|
| index[0..5] | 0xB87800 | `00 00  00 00  a6 05  d5 07  ef 07  f8 0a` - card 1 has no record, card 2's record is at +1446 (0x5A6) |
| card 2 record | 0xB87DA6 | `df 48 08 7e 09 d6 88 0a 27 ...` - count 223, first group: 2+8=638, 2+9=470 |
| card 4 record | 0xB87FEF | `00 c9 80 06 1f ...` - count byte 0 => count = 511-0xC9 = 310 |
| end of data | 0xB975EA | `... cf 27 ff ff ff ...` - 65,002 bytes used (last byte at +0xFDE9), 534 free, 0xFF fill to 0xB97800 |

Totals: 578 cards own a record, 25,131 pairs, 4 records use the two-byte count form
(cards 4, 7, 122, 138), 293 records have an odd count, 50 pairs are "card with itself".

### Record format (what `getUint8` chains in `extractData` decode)

    u16 index[723]           index[id] = byte offset of card id's record, 0 = no record; index[0] unused (0)
    record:
      u8  count              1..255, or
      u8  0, u8 511-count    for 256..511 (so max 511 partners per card)
      5-byte groups, each holding TWO (partner, result) entries of 10-bit ids:
        g[0] = p1>>8 | (r1>>8)<<2 | (p2>>8)<<4 | (r2>>8)<<6
        g[1] = p1 & 0xFF   g[2] = r1 & 0xFF   g[3] = p2 & 0xFF   g[4] = r2 & 0xFF
      odd count: the last group is written as only 3 bytes (g[0..2]) - stock and site alike

A pair is stored once, under the SMALLER id, with the larger id as partner (the lookup sorts its
arguments). Records sit in card order right after the index. Only the first entry for a given
partner is reachable (the site collects duplicates into arrays but writes `[0]`).

## 2. What the site writes (`setObjectValues` / `salvar`)

For "Save on" = one field it rewrites that block's table; for "All Fields" (setID 0) it loops
blocks 0..6 (`offset = 12089344 + 481280*block`). Per block:

| step | bytes |
|---|---|
| index[0] | `00 00` |
| index[id], id = 1..722 | u16 little-endian offset (or 0) |
| records | in card order from offset 1446: count (1 or 2 bytes), groups of 5, 3-byte tail for odd counts; partners sorted ascending; one result per pair |
| fill | `FF` from the end of data to +65536 |

Capacity check ("SAVE PANEL" -> Used/Free Memory): `necessarySize = 1446 + sum(5*floor(n/2) +
(n<256 ? 1 : 2) + (n odd ? 3 : 0))`; save refuses when `65536 - necessarySize < 1`. That is the
real limit: the loader copies exactly 0x10000 bytes and offsets are u16.

**Offset discrepancy.** `offset_base` is 12,089,344 = 0xB88000 = block + 0x25000. The game's
loader (section 3) takes the table from block + 0x24800 = 0xB87800, and the bytes at 0xB88000 are
the middle of card 4's record body. Fed the stock US file, the site's extractor produces 722
"cards" with 54,831 nonsense pairs (`fusion_table.py dump --site-offsets`), and its writer would
put a valid table 2 KiB past where the game reads it, clobbering the second half of the real one
while leaving the first 0x800 bytes (index + first records) stock. The same +0x800 is in the
equipmaker tool (0xB85800 vs 0xB85000). Whether the site's authors work from a differently
built WA_MRG.MRG or this is simply a bug cannot be decided from the client code; the initial-deck
tool's offsets (further into the same file) match the disc exactly, so a global shift is ruled
out. `scripts/fusion_table.py` uses the game's offsets and offers `--site-offsets`.

## 3. What the game does with it

### Loading: `Main_RunDuel` -> `func_800179F4` -> `func_80014E1C(0, 0, 0x16C6 + 235*gDuel_bTerrain, 0xEB, cb=0x800171A8)`

    80017A34  lui   v1, %hi(gDuel_bTerrain)
    80017A38  lbu   v1, %lo(gDuel_bTerrain)(v1)      ; 0x8009B364
    80017A4C  sll   a2, v1, 4  / subu / sll 2 / subu / sll 2 / subu   ; a2 = 235*t
    80017A64  jal   func_80014E1C                    ; a3 = 0xEB sectors, callback on stack
    80017A68  addiu a2, a2, 0x16C6                   ; first sector of the block

The 235-sector read is split by the callback at 0x800171A8 (decomp still calls it
`select_sound_preset`; findings F14 already says that name is wrong). It is called with a stage
index 0..12, dispatches through the jump table at 0x800100C0 and sets destination (+8/+0xC of the
request) and byte length (+0x1C) for the next chunk; chunks are consecutive in the block:

| stage | block offset | length | destination |
|---|---|---|---|
| 0 | +0x00000 | 0x20000 | VRAM stream, rect (0x300,0x100) 64x16 per sector |
| 1 | +0x20000 | 0x2000 | RAM buffer `*D_8009B118` |
| 2 | +0x22000 | 0x2800 | **gDuel_awEquipTable 0x8017A1D8** (after `LoadImage2` of the stage-1 buffer) |
| 3 | +0x24800 | 0x10000 | **gDuel_aFusionTable 0x8017C2D8** |
| 4 | +0x34800 | 0x800 | gDuel_awRitualData 0x801799D8 |
| 5 | +0x35000 | 0x1000 | `*D_8009B118` |
| 6 | +0x36000 | 0x10000 | VRAM stream, rect (0x200,0x100) |
| 7 | +0x46000 | 0x16000 | 0x80146000 - the duel overlay code (`D_800100A8+0x134`) |
| 8 | +0x5C000 | 0x1800 | gAiScript_abHandScript 0x801A8000 |
| 9 | +0x5D800 | 0x1800 | D_801A9800 |
| 10 | +0x5F000 | 0x4000 | VRAM stream, rect (0x340,0) |
| 11 | +0x63000 | 0x2800 | load arena[0] 0x80100000 |
| 12 | +0x65800 | 0x10000 | VRAM stream, rect (0x280,0x100) - the only terrain-specific sectors |

Lengths sum to 0x75800 = 235 sectors. Consequences: the equip chunk is 0x2800 bytes but the
fusion chunk starts 0x2100 later in RAM, so the last 0x700 bytes of the equip area are dead; the
fusion table is followed in RAM by whatever was there (0x8018C2D8 onward is not part of this load).
`func_8001798C` is a copy of the same loader with no caller anywhere in the EXE or the duel
overlay: **the block is loaded once per duel, for the terrain the duel starts on.** Playing a
Field magic card mid-duel changes `gDuel_bTerrain` for the stat bonuses but does not reload the
tables, so a per-terrain fusion set only ever selects by starting terrain.

### Lookup: `fusion_table_lookup` 0x80019A60 (decomp `src/fusion.c`, matched)

    int fusion_table_lookup(int a, int b) {
        u16 *base = fusion_table; u8 *p; int off, cnt, g0;
        if (b < a) swap(a, b);
        off = base[a];  if (off == 0) return 0;
        p = (u8 *)base + off;
        cnt = p[0];  if (cnt == 0) { cnt = 0x1FF - p[1]; p++; }  p++;
        do {
            g0 = p[0];
            if ((((g0 << 8) & 0x300) | p[1]) == b) return ((g0 << 6) & 0x300) | p[2];
            if ((((g0 << 4) & 0x300) | p[3]) == b) return ((g0 << 2) & 0x300) | p[4];
            p += 5; cnt -= 2;
        } while (cnt > 0);
        return 0;
    }

    80019AD0  lbu  a2, 0(a0)          ; g0
    80019AD4  lbu  v1, -2(a3)         ; p[1]
    80019AD8  sll  v0, a2, 8 / andi 0x300 / or v1
    80019AE4  beq  v0, a1 -> hit1 (result = (g0<<6)&0x300 | p[2])
    80019AEC  sll  v0, a2, 4 / lbu v1, 0(a3) / andi / or
    80019AFC  beq  v0, a1 -> hit2 (result = (g0<<2)&0x300 | p[4])
    80019B04  addiu t0, t0, -2
    80019B08  bgtz t0, loop

Callers: the summon resolver `func_8001A280` (fusion table first, then equip table both ways -
see the recomp's `psx_fusion_db.c` header), the AI planners `func_80027228`, `func_80026DC8` and
`Ai_CompleteFusion` 0x800727C0. Player and AI share the table, so an edit changes both.

### The glitch fusions (site panel "GLITCH FUSIONS")

For an odd count the loop still tests the second half of the final group, but the record only
has 3 bytes there: `p[3]` is the NEXT record's count byte and `p[4]` its first g0. Stock example,
card 22 (record at +0x1BA2, count 1): tail `00 52 d9` (22+82=217), followed by card 23's record
`1f 48 ...` -> the game also answers 22 + 31 = 72.

**Counting criterion.** "Glitch fusion" here means a pair the game actually answers differently
from what the table intends, established by emulating `fusion_table_lookup` over all 261,003
unordered pairs and diffing against the decoded entries. By that measure the stock table has
**15**. A raw scan of the trailing halves counts far more, because most decodes are unreachable -
of the 293 odd-count records:

| trailing half | count |
|---|---|
| decodes to result 0 (no fusion either way) | 30 |
| partner id < the record's own card id - the lookup sorts its arguments, so that record is never the one consulted for the pair | 245 |
| partner id out of range (> 722) | 1 |
| partner already appears earlier in the same record, so the loop returns before reaching the tail | 2 |
| **reachable: the game answers a pair the table does not contain** | **15** |

(263 nonzero decodes and 260 "nonzero, in range, not already a pair in that record" are the counts
you get before the partner-ordering filter; the 245-row is the whole of the difference.) The 15:

    22+31->72   23+147->4   26+138->4   31+34->84   40+126->4   45+170->136  61+144->136
    64+168->72  66+98->132  74+150->72  90+130->136 96+231->136 120+166->132 127+128->72
    167+225->64

(`fusion_table.py dump` prints them; `verify` treats them as expected.) The site's advice "add
or delete one fusion in the card-1 list" works because it flips the record's parity or changes
what follows. `fusion_table.py import --safe-tails` writes 5-byte zero-padded tails instead,
which removes them for good at +2 bytes per odd record - the stock set does not fit that way
(needs 586 bytes, 534 are free), a trimmed set does. Zero padding is safe because the tail's g0
has its upper nibble clear, so partner2 decodes to 0, which no card id can match.

Other limits the format imposes: 511 partners per (smaller) card id; 65,536 bytes total and
every record must start below 0x10000; a record with count 0 is impossible to store (index 0
means "none"); the game finds only the first entry per partner.

## 4. Recomp options

1. **Ship a patched WA_MRG.MRG / disc** made with `scripts/fusion_table.py import ... --terrain all`.
   Zero code; identical to what the site produces (at the game's offset). Check first whether the
   recomp validates the disc hash (`disc_identity.h`).
2. **Overwrite the RAM copy after each load (data patch).** A vblank hook that waits until the
   duel block has arrived, then writes a host-side 0x10000-byte table to 0x8017C2D8 (and the equip
   table to 0x8017A1D8) with `psx_mod_write_byte/half`. "Arrived" = stage 4 landed: u16 at
   `gDuel_awRitualData` 0x801799D8 == 670 and the stock sentinel `index[2] == 1446` at 0x8017C2DC
   (the recomp's `psx_fusion_db_ready()` already checks this shape). Re-arm when the sentinel
   disappears (the tables read as zeros outside a duel), so every duel gets the mod table. Keep
   the 64 KiB and 511-partner limits, or lose the packed format entirely with option 3.
3. **Native replacement of the lookup.** `psx_mod_register_function_entry_plugin` on
   `fusion_table_lookup` 0x80019A60 (needs the address in game.toml `mod_function_entry_funcs`
   and a regenerate, as `psx_fusion_assist.c` notes): read a0/a1 from `cpu->gpr[4..5]`, answer
   from an unbounded host table (CSV from `export`), set `gpr[2]` and return to `gpr[31]`. Covers
   the AI callers too, removes the size cap, the 3-byte-tail glitch and the one-result-per-pair
   rule, and can consult `gDuel_bTerrain` live so field cards can change fusions mid-duel.
   `psx_fusion_db.c` must then read the same host table instead of guest RAM.

## 5. Decomp findings (proposed)

- `0x800171A8` | it is the duel-block streaming callback: stage index 0..12 -> jump table
  0x800100C0, sets chunk destination/length per the table in section 3; never a sound routine
  (agrees with F14) | `Duel_LoadDataStage`
- `0x800100C0` | 13 code pointers, the stage dispatch table of the above | `gDuel_apLoadDataStages`
- `0x800179F4` | duel start loader: block `0x16C6 + 235*gDuel_bTerrain` (235 sectors) via
  0x80014E1C with the callback above, then opponent deck pool: 3 sectors at `0x1D33 + 3*gDuel_bOpponentID`
  -> gDuel_awOpponentDeckPool 0x801781D8 | `Duel_LoadTerrainBlockAndDeck`
- `0x8001798C` | same block load without the deck part; no caller in the EXE or the duel overlay
  (checked by opcode `0x0C005E63` and by pointer) | `Duel_ReloadTerrainBlock_unused`
- `WA_MRG +0xB87800 + t*0x75800` (0x10000 B) | stock fusion table, seven identical copies, 578
  records / 25,131 pairs / 65,002 bytes; layout as in section 1; 15 tail-overlap fusions | data
  for `gDuel_aFusionTable`
- `WA_MRG +0xB85000 + t*0x75800` (0x2800 B, 0x2100 live) | stock equip table (see ../equipmaker) |
  data for `gDuel_awEquipTable`
- `WA_MRG +0xB97800 + t*0x75800` (0x800 B) | ritual data, u16 rows `ritual, tribute1..3, result`
  starting `670, 27, 38, 58, 364` | data for `gDuel_awRitualData`
- `0x80146000` duel overlay = block + 0x46000 (in-file sector 0x1752 + 235*t), 0x16000 B - matches
  `tools/extract_overlay.py`'s seven copies at LBA 16072 + 235*k
- `psx_fusion_db.c` comment "every trailing half decodes to a result of 0" is wrong for the
  shipping data: 263 of 293 odd records have a nonzero trailing decode, 15 of them are matching
  card pairs (list above). The recomp's `pair_lookup` copies the game's loop, so it already
  answers like the game; only the comment needs fixing.

## 6. Open questions

- Why the site's constants are one sector past the stock table (same in equipmaker). Nothing
  server-side is involved: the only network call is the analytics POST to `api/v2/tools`
  (`saveChange` on the `create` event); the whole edit is client-side.
- The site's SLUS reads (`getCardInfo`: names at 0x1C6000/0x1C6800, stats at 0x1C4A40+4*id,
  descriptions via the u16 offsets at 0x1B0A00) are display-only here; not re-verified in this folder.
- Whether the seven per-terrain copies were ever meant to differ (the game's loader is the only
  reason the site offers "Save on: field"), and whether `func_8001798C` is reachable through
  some pointer table outside the EXE image (nothing found).
