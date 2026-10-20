# EQUIP MAKER tool

Route: `extend/tools/equipmaker` (site version string V.220518 [BETA]). Inputs: SLUS_014.11
(`.11`, read only, card names/types for the UI) and WA_MRG.MRG (`.mrg`, 36,700,160..45,088,768
bytes; the file that gets edited), optionally an .xlsx made from
`site/Assets/files/EquipTemplate.xlsx` (columns EQUIP, CARD). Client-side only; the whole
WA_MRG.MRG is downloaded back.

Purpose: edit the **equip compatibility table** - which monsters each Equip magic card (type 23:
ids 301-328, 651, 652, 654, 657, 658, 659, 668) can be "fused" onto. The site shows the list per
equip, the reverse view per monster, batch-adds every card matching a filter set to one equip,
imports from Excel, and re-packs the table into one or all seven per-terrain copies.

Status: format decoded and proved against the game's loader + lookup; disc-verified; offline
clone `scripts/equip_table.py` (dump / export / import / verify / lookup / restore; import and
restore reproduce the stock bytes exactly). **The site's file offset is one sector (0x800) later
than where the stock US disc keeps the table** - same as fusionmaker, see section 2. Not yet built
as a recomp mod. Raw notes: `NOTES-raw.md`; the shared loader analysis is in
`../fusionmaker/README.md` section 3.

## 1. Where the table lives

Part of the per-terrain duel data block (`../fusionmaker/README.md` sec. 1/3), stage 2 of the
duel loader:

    block(t) = in-file sector 0x16C6 + 235*t, t = gDuel_bTerrain 0..6   (WA_MRG 0xB63000 + t*0x75800)
    equip table = block + 0x22000, 0x2800 bytes on disc  ->  RAM 0x8017A1D8 (gDuel_awEquipTable)
    only the first 0x2100 = 8448 bytes survive: stage 3 puts the fusion table at 0x8017C2D8

| terrain t | site name | WA_MRG offset (game) | in-file sector | disc LBA | site's offset |
|---|---|---|---|---|---|
| 0 | Normal | 0xB85000 | 0x170A | 16000 | 0xB85800 |
| 1 | Forest | 0xBFA800 | 0x17F5 | 16235 | 0xBFB000 |
| 2 | Wasteland | 0xC70000 | 0x18E0 | 16470 | 0xC70800 |
| 3 | Mountain | 0xCE5800 | 0x19CB | 16705 | 0xCE6000 |
| 4 | Meadow | 0xD5B000 | 0x1AB6 | 16940 | 0xD5B800 |
| 5 | Sea | 0xDD0800 | 0x1BA1 | 17175 | 0xDD1000 |
| 6 | Dark | 0xE46000 | 0x1C8C | 17410 | 0xE46800 |

Stock bytes (terrain 0, verified on the US disc; all seven copies identical):

| what | offset | bytes |
|---|---|---|
| first group | 0xB85000 | `2d 01 3f 00 0c 00 0f 00 1a 00 1b 00 1d 00 21 00 ...` = equip 301, 63 cards: 12, 15, 26, 27, 29, 33, ... |
| terminator | 0xB87018 | `d2 02 00 00 ff ff ff ff` - last member 722 of equip 668, then key 0 at 0xB8701A |
| fill | 0xB8701C..0xB87800 | `FF` |
| site's base | 0xB85800 | `0f 02 10 02 11 02 15 02 ...` - the middle of equip 303's member list |

Stock content: 34 groups, 4,041 memberships, 8,220 bytes used of 8,448 live (228 free). Members
are ascending and unique; keys ascending. Per equip (count): 301:63 302:60 303:292 304:82 305:149
306:114 307:79 308:226 309:16 310:30 311:120 312:64 313:59 314:92 315:76 316:105 317:57 318:1
319:97 321:141 322:78 323:91 324:121 325:62 326:111 327:138 328:114 651:102 652:1 654:31
657:621 (Megamorph) 658:1 659:26 668:621. Card 320 has no group.

### Record format

    repeat:  u16 key (equip card id)   u16 count   u16 member[count]
    end:     u16 0

Nothing else - no index, no length. Everything is little-endian u16.

## 2. What the site writes (`setObjectValues` / `salvar`)

For "Save on" = one field it rewrites that block; for "All Fields" (setID 0) blocks 0..6
(`offset = 12079104 + 481280*block`). Per block: for every card id (ascending) with a non-empty
list: `u16 id, u16 n, u16 members[n]` (members kept sorted/unique on add); then `u16 0`; then `FF`
from there to +8448 (only; bytes 8448..10240 of the region are left as they were). Capacity check
("SAVE PANEL"): `necessarySize = sum(4 + 2n) + 2 + 1`, refuse when `8448 - necessarySize < 1`.

The extractor (`extractData`) walks from the base reading `u16 key, u16 count`, stops at the first
pair that is not both in 1..722, and keeps only the first occurrence of a key. Fed the stock US
file at the site's 0xB85800 it reads key 527, count 528 and produces garbage
(`equip_table.py dump --site-offsets`: 10 groups, walk runs past the live area). The game's offset
is 0x800 earlier (proved by the loader's stage table). The site can store any card id as a key,
not only equips; the game will happily look it up (see below).

## 3. What the game does with it

`equip_table_lookup` 0x80019A08 (decomp `src/fusion.c`, matched) - returns `card` if `card` is
in `equip`'s group:

    int equip_table_lookup(int equip, int card) {
        u16 *p = equip_table; int key, cnt;
    top:
        key = *p; if (key == 0) return 0;
        cnt = p[1]; p += 2;
        if (key == equip) {
            do { if (card == *p) return card; p++; } while (--cnt != 0);
            return 0;
        }
        p += cnt; goto top;
    }

    80019A10  lhu  v0, 0(v1)        ; key
    80019A18  beqz v0 -> return 0
    80019A20  lhu  a2, 2(v1)        ; count
    80019A24  bne  v0, a0 -> skip: v1 += 4 + 2*count
    80019A2C  lhu  v0, 0(v1)        ; member
    80019A34  beq  a1, v0 -> return a1
    80019A38  addiu a2, a2, -1
    80019A3C  bnez a2 -> next member

Callers: the summon resolver `func_8001A280` (after the fusion table fails it tries
`equip_table_lookup(second, first)` then `(first, second)`; whichever returns, that monster
survives and gets +500 ATK/DEF, +1000 for Megamorph 657 - traced in the recomp's
`psx_fusion_db.c`), the AI's `AiScript_FindEquipTarget` 0x8007249C, `func_80026DC8` and
`Ai_CompleteFusion` 0x800727C0. The table is loaded once per duel for the starting terrain
(no mid-duel reload; `../fusionmaker/README.md` sec. 3).

Consequences / limits:
- Live capacity is 8,448 bytes including the terminator. A group that crosses 0x8017C2D8 is
  overwritten by the fusion index: `index[0]` is 0, so a table of exactly 0x2100 bytes still
  terminates, anything longer gets the fusion index parsed as keys/counts.
- A group with count 0 hangs the game when its key is looked up (`--cnt != 0` loop on 0 wraps).
  The site never writes empty groups; neither does the script.
- Duplicate keys: only the first group is reachable. Order inside a group is irrelevant.
- A key does not have to be an equip card: any card A whose group contains B makes "A + B" keep B
  and power it up - that is how "magic cards that fuse" behave and how a mod could add
  equip-like behaviour to arbitrary cards. Whether a card is treated as an equip elsewhere
  (bonus value, animation) is decided by its type in the SLUS card table, not by this table.
- The equip attempt only happens when the fusion table has no entry for the pair; a fusion entry
  for (monster, equip) wins.

## 4. Recomp options

1. **Patched WA_MRG.MRG / disc** via `scripts/equip_table.py import ... --terrain all` - same
   effect as the site, at the offset the game reads.
2. **RAM overwrite after load**: vblank hook, wait for the block (u16 at 0x801799D8 == 670 and
   the stock head `301, 63` at 0x8017A1D8), then write up to 0x2100 bytes of a host table with
   `psx_mod_write_half`; re-arm when the area reads as zeros again. Fits naturally beside the
   fusion-table stamp (one hook, both tables).
3. **Function-entry hook on 0x80019A08** (`psx_mod_register_function_entry_plugin`, address must
   be in game.toml `mod_function_entry_funcs`): answer from a host set of (equip, card) pairs, set
   `gpr[2]` to a1 or 0 and return via `gpr[31]`. No 8 KiB cap, covers the AI callers, and can key
   on `gDuel_bTerrain` live. `psx_fusion_db.c`'s `equip_lookup` should then read the same host set.

## 5. Decomp findings (proposed)

- `WA_MRG +0xB85000 + t*0x75800` (0x2800 B, 0x2100 live) | stock equip table, seven identical
  copies, 34 groups / 4,041 members / 8,220 B, format `u16 key, u16 n, u16 member[n]`, 0-terminated |
  data for `gDuel_awEquipTable`
- `0x800171A8` stage 2 | copies 0x2800 bytes from block +0x22000 to 0x8017A1D8 and first uploads
  the previous 0x2000-byte chunk with `LoadImage2` to VRAM (0x100,0xF0) 256x16 | part of
  `Duel_LoadDataStage` (see fusionmaker)
- `0x80019A08` `equip_table_lookup` | count-0 group is an infinite loop; first matching key wins |
  name already in symbol_addrs (fine as is; a `Duel_` prefix would be `Duel_EquipTableLookup`)

## 6. Open questions

- Same offset discrepancy as fusionmaker (+0x800); nothing server-side (only the analytics POST
  to `api/v2/tools`).
- The site's "Show only equip cards" filter uses `data.type == 23` from the SLUS card table
  (and `type < 20` for the monster list) - consistent with the recomp's type codes, not
  re-verified here.
- Whether anything else reads bytes 0x2100..0x2800 of the on-disc region before the fusion
  chunk overwrites them (the DMA lands them in RAM briefly); nothing found, treated as dead.
