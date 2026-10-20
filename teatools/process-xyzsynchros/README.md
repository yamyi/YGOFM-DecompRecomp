# XYZ & Synchro summons (process tool)

Route: `extend/tools/process/xyzsynchros`. Inputs: SLUS_014.11 (`.11`, 1..5 MB) and WA_MRG.MRG
(`.mrg`, 35..43 MB). Version on the page: V.231009 [BETA].
Purpose: two new fusion rules on top of the stock fusion table. XYZ: two monsters of the same level
L and the same type T fuse into `xyz[L][T]`. Synchro: a tuner monster plus a non-tuner of the same
type fuse into `synchro[L1+L2][T]`. The site writes a 464-byte MIPS routine plus three tables into the
last 1728 bytes of the duel's 64 KB fusion-table block (all 7 field copies) and redirects
`fusion_table_lookup` to it with one 8-byte hook in the EXE. Panels: install ("process enabled"
check on both files), XYZ / Synchro / Tuner editors per level, "repeat in all fields" or one field.
The page also calls `api/v2/toolcontrol/genhash` on save (session-gated, not needed for the bytes).
Status: decoded, stock bytes verified (WA copies identical, EXE hook stock words checked), script
round-trips byte-exact, not yet built as a recomp mod. **Installing on a stock WA_MRG destroys
fusion records of 63 cards** (see below).
Script: `scripts/xyz_synchro.py` (inspect / apply / export / restore). Patch dump + disassembly:
`patch/` (SLUS hook `hook_*`, WA routine `xyz_00b97140.*`). Raw notes: `NOTES-raw.md`.

## 1. The EXE hook

| | |
|---|---|
| file offset | 0xA260 (8 bytes) |
| RAM | 0x80019A60 = first two instructions of `fusion_table_lookup` (`asm/matchings/fusion/fusion_table_lookup.s`) |
| stock | `3C028018 2443C2D8` = `lui v0,0x8018; addiu v1,v0,-0x3D28` (v1 = gDuel_aFusionTable 0x8017C2D8) |
| patched | `08062F06 00000000` = `j 0x8018BC18; nop` |

Callers: `func_80027228` (player fusion, 0x800272C0 / 0x800274A4) and `Ai_CompleteFusion` (0x80072850).
Signature `fusion_table_lookup(a0 = card A, a1 = card B) -> result id or 0`.

## 2. The WA_MRG block (JS `F`, 464 bytes) and tables (JS `I`)

| what | WA_MRG offset (field copy 0) | in-file sector | RAM | size |
|---|---|---|---|---|
| routine | 0xB97140 | 0x172E + 0x140 | 0x8018BC18 | 464 B (416 code + 48 zero) |
| xyz table | 0xB97310 | | 0x8018BDE8 | u16[15 levels][20 types] = 600 B, index (L-1)*20+T |
| synchro table | 0xB97570 | | 0x8018C048 | u16[14 sums 2..15][20 types] = 560 B, index (S-2)*20+T |
| tuner bits | 0xB977A0 | | 0x8018C278 | 91 B, card c at byte (c-1)/8, bit 7-((c-1)&7) |
| end of block | 0xB97800 | 0x172F | 0x8018C2D8 | |

Same layout in the other six field copies at +k*0x75800 (k = 1..6: 0xC0C940, 0xC82140, 0xCF7940,
0xD6D140, 0xDE2940, 0xE58140). The tool checks copy 0 only, writes all 7 (or one with "save in
this field"). Address arithmetic: the duel loader (case at 0x800172D8 in the misnamed
`select_sound_preset` 0x800171A8) reads 0x10000 bytes into `fusionTable` 0x8017C2D8, so WA 0xB87800
(sector 0x170F) <-> 0x8017C2D8 and the block ends exactly at 0x8018C2D8. The 7 duel-overlay copies
(0x80146000 image) sit at 0xBA9000 + k*0x75800 in the same field copies.

### Stock content of those 1728 bytes (verified on the US disc)

The fusion block is full: the u16 offset table (723 entries at the start) points to records up to
+0xFDEC and the rest (+0xFDEC..+0x10000) is 0xFF padding. Offsets +0xF938..+0xFDEC hold the
fusion records of **cards 581..712** (63 cards with data there: 581-589, 591-610, 612, 616, 618,
620-623, 625-629, 631-633, 635-638, 641-644, 648, 651, 652, 655, 657-659, 665, 686, 687, 712).
After install, `fusion_table_lookup` still follows their offsets and parses code/table bytes as
records, so those cards' fusions become garbage. The page says as much ("the last 1728 bytes of the
total data reserved for merges are required ... the data will be replaced"): the intended workflow
is to rebuild the fusion table with the site's fusion editor first so it ends before +0xF940.
`restore` puts the stock 1728 bytes back (embedded in the script).

## 3. The routine (`patch/xyz_00b97140.dis`, entered with a0/a1 = the two card ids)

    lvA = D_801D5332[a0] & 0xF ; lvB = D_801D5332[a1] & 0xF      ; level nibble of each card
    if lvA == 0 or lvB == 0: goto stock
    if lvA == lvB:                                               ; ---- XYZ
        tA = gDuel_adwCardStats[a0] >> 26 ; tB = ... [a1] >> 26  ; type (6 bits)
        if tA == tB:
            r = xyz[(lvA-1)*20 + tA]; if r: return r
    tunA = tunerbit(a0); tunB = tunerbit(a1)                     ; ---- Synchro
    if tunA + tunB == 1:
        if tA == tB:
            s = lvA + lvB
            if s > 1: r = synchro[(s-2)*20 + tA]; if r: return r
    stock:  v0 = 0; lui v0,0x8018; addiu v1,v0,-0x3D28; j 0x80019A68   ; resume fusion_table_lookup

`tunerbit(c)`: byte `tuner[c >> 3]`, bit `8 - (c & 7)` counted from bit 0. For c % 8 == 0 that is bit 8
of the *next* byte, i.e. always 0, while the site stores card 8i+8 in bit 0 of byte i. **Cards whose
id is a multiple of 8 can never act as tuners in-game** even though the editor accepts them.
Other quirks: the routine skips the stock `a0 <= a1` swap (it is symmetric, so harmless); a synchro
sum above 15 indexes past the 560-byte table (row (s-2)*40 bytes) into the tuner bits and beyond
0x8018C2D8; the type compare uses 6 bits where the stock code masks 5; result ids are returned raw
(the stock path returns 9-bit ids too). The synchro rule ignores the stock "tuner must be level..."
notion entirely: only the tuner flag, type equality and the level sum matter. The stock lookup only
runs when neither rule produced a result, so xyz/synchro entries shadow stock fusions of the same pair.

Stock fusion record format (for reference, from `fusion_table_lookup`): `u16 off[723]`; record =
`u8 n` (n == 0 -> `n = 0x1FF - next byte`) then 5-byte groups holding two (partner, result) pairs:
byte0 carries the high 2 bits of the four 9-bit ids, bytes 1..4 the low 8 bits.

## Recomp options

1. **Native rule, no disc edit.** Hook `fusion_table_lookup` entry (0x80019A60, base EXE) with a
   native function: read level/type from `gDuel_adwCardStats` / `D_801D5332`, consult mod-owned
   xyz/synchro/tuner tables (CSV via `xyz_synchro.py export`), fall back to the stock function.
   This keeps all stock fusions and fixes the id%8 tuner bug.
2. **Site-file compatibility.** If a player's WA_MRG carries the block, the resident copy is at
   0x8018BC18 during a duel; a frame hook can verify `psx_mod_read_word(0x8018BC18) == 0x3C02801D`
   and leave it alone; no extra work.
3. **Disc-side clone** (not recommended): write the 1728 bytes into the 7 copies as the site does,
   but only after compacting the fusion table so records end before +0xF940.

## Decomp findings (proposed)

- 0x8017C2D8..0x8018C2D8 | 64 KB fusion block loaded whole (`lui v1,1` at 0x800172F4) from WA_MRG 0xB87800 + k*0x75800 (sector 0x170F + 0xEB*k, k = field 0..6, copies byte-identical); stock records end at +0xFDEC, 0xFF fill after; record format as above | `gDuel_aFusionTable` (keep) + note the extent
- WA 0xBA9000 + k*0x75800 | the 7 duel-overlay copies (header sig `18 00 00 00 / 00 10 00 00 x3` + "Error:In Effect"), i.e. sector 0x1752 + 0xEB*k; field copy stride 235 sectors | overlay location
- 0x801D5332 | u8[723] indexed by card id: low nibble level, high nibble attribute (site `readValues`, used by the xyz routine and by init_container_entry_objs) | `gDuel_abCardLevelAttr`
- 0x801D4240 | `gDuel_adwCardStats`: bits 0-8 ATK/10, 9-17 DEF/10, 18-21 guardian star 2, 22-25 guardian star 1, 26-31 type (site bit layout, matches the `sra 26 & 0x1F` readers) | field layout note
- 0x800171A8 | duel-data streaming loader (cases select target: fusionTable, equipTable 0x8017A1D8, ritualData 0x801799D8, overlay, ...), currently named `select_sound_preset` | rename candidate `Duel_LoadDataCase`

## Open questions

- Why the stock free space is zero: whether Konami's table was packed to the byte or the block is
  simply followed by another loader case (the loader size is exactly 0x10000 so nothing past
  0x8018C2D8 comes from this read).
- The `genhash` call on save: probably a licence/usage token; not needed offline.
- Field copies 8..10 used by the card-colour tool (0xF07800 etc.) do not contain a fusion block; the
  xyz tool only touches the 7 duel copies.
