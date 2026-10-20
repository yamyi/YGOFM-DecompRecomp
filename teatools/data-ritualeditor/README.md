# Ritual Editor

Route: `extend/tools/data/ritualeditor`. Inputs: SLUS_014.11 (read only: card names, stats and
descriptions for the pickers) and WA_MRG.MRG (edited and downloaded back; the loader is the shared
`Tree` component, "to-load: SLUS_014.11, WA_MRG.MRG", size limits live in chunk-common).
UI "Ritual Editor | V. 20251123", client-side; the analytics POST is `api/v2/tools` with `tipo` 43
(comments box `guia` 53). Card art in the pickers is read from WA_MRG.MRG at
`0x169000 + 0x3800*(id-1)` (102x96, 8bpp, palette at `0x16B5C0 + 0x3800*(id-1)`).
Script: `scripts/ritual_editor.py` (dump / verify / apply / restore, on WA_MRG.MRG or a copy of the
MODE2/2352 disc image). Raw notes: `NOTES-raw.md`.

Purpose: edit the game's ritual recipes — the activating Ritual spell card, the three exact
monsters that must be on your field, and the monster that replaces them.

Status: table located on disc and in RAM, loader and consumer found in the decomp, stock table
verified on the US disc (all 7 copies identical), script round-trips byte-for-byte. Not yet built
as a recomp mod.

## 1. The table

| | |
|---|---|
| WA_MRG.MRG offset | `0xB97800 + 0x75800 * k`, k = 0..6 (one copy per terrain package) |
| in-file sector / disc LBA | `5935 + 235k` / `16037 + 235k` |
| size the game copies | 0x800 bytes (one sector) |
| RAM | `0x801799D8` = `gDuel_awRitualData` (base EXE address, zero in SLUS; filled from disc per duel) |
| record | 5 x u16 LE: `type<<10 \| spell`, `mat1`, `mat2`, `mat3`, `result` (card ids 1..722, 10 bits) |
| end of list | a record of five zero halfwords; the rest of the sector is 0xFF |

The site reads copy 0, masks every field with 0x3FF (`type` = bits 10-11 of the first word, always
0 in stock and locked to "Normal Ritual" in the UI), stops at the first all-zero record or after 24,
and on save writes 24 slots (unused ones zeroed) plus a zero record at +240 into **all seven
copies** (`multiSetWord`, stride 481280). The 7 copies are the 7 terrain packages (see 3), which is
what the download text means by "the same configuration will be used for every field type".

Stock recipes (spell -> materials -> result), verified on disc:

    670 Black Luster Ritual        27 Beaver Warrior, 38 Gaia the Fierce Knight, 58 Kuriboh   -> 364 Black Luster Soldier
    671 Zera Ritual                85, 298, 377                                               -> 360 Zera The Mant
    673 War-lion Ritual            201, 403, 483                                              -> 356 Super War-lion
    674 Beastry Mirror Ritual      186, 261, 595                                              -> 365 Fiend's Mirror
    675 Ultimate Dragon            1, 1, 1 (three Blue-eyes)                                  -> 380 Blue-eyes Ultimate Dragon
    665 Curse of Millennium Shield 255, 296, 629                                              -> 362 Millennium Shield
    666 Yamadron Ritual            29, 31, 101                                                -> 357 Yamadron
    667 Gate Guardian Ritual       371 Sanga, 372 Kazejin, 373 Suijin                         -> 374 Gate Guardian
    676 Commencement Dance         249, 395, 511                                              -> 701 Performance of Sword
    677 Hamburger Recipe           14, 295, 547                                               -> 702 Hungry Burger
    678 Revival of Sennen Genjin   3, 64, 453                                                 -> 703 Sengenjin
    679 Novox's Prayer             160, 161, 535                                              -> 704 Skull Guardian
    680 Curse of Tri-Horned Dragon 6, 47, 571                                                 -> 705 Tri-horned Dragon
    691 Revived of Serpent Night Dragon 168, 294, 604                                         -> 706 Serpent Night Dragon
    692 Turtle Oath                89, 449, 451                                               -> 710 Crab Turtle
    693 Contruct of Mask           102, 182, 220                                              -> 720 Mask of Shine & Dark
    694 Resurrection of Chakra     178, 269, 288                                              -> 709 Chakra
    695 Puppet Ritual              166, 405, 416                                              -> 715 Psycho-Puppet
    696 Javelin Beetle Pact        52, 480, 533                                               -> 717 Javelin Beetle
    697 Garma Sword Oath           239, 378, 621                                              -> 716 Garma Sword
    698 Cosmo Queen's Prayer       266, 635, 638                                              -> 708 Cosmo Queen
    699 Revival of Skeleton Rider  146, 479, 485                                              -> 719 Dokurorider
    700 Fortress Whale's Oath      436, 441, 542                                              -> 718 Fortress Whale
    721 Dark Magic Ritual          7, 35 Dark Magician, 417                                   -> 722 Magician of Black Chaos

Site rules: spell picker = cards with type 22 (Ritual); result and material pickers = type < 20
(monsters); "Add New Combination" (disabled past 24) inserts `695 / 1,1,1 -> 380`; Duplicate /
Remove edit the list; only the WA file is offered for download.

## 2. What the game does with it

**Loading.** `func_8001798C` (called from the duel entry path) issues one disc request
`func_80014E1C(0, 0, 0x16C6 + 235*gDuel_bTerrain, 0xEB, callback=0x800171A8, 0, 0)`: a 235-sector
"terrain package" (sector 5830 + 235k). The callback (misnamed `select_sound_preset` in the
decomp; a verbatim asm transcription) is a state machine that copies the package's pieces to their
homes; the case at 0x80017300..0x8001731C sets destination `gDuel_awRitualData` and size 0x800.
Neighbouring cases do the same for `gDuel_awEquipTable` (0x8017A1D8, 0x2800 bytes) and
`gDuel_aFusionTable` (0x8017C2D8, 0x10000 bytes). Package layout measured on disc: +105 sectors =
this table, +140 = the duel overlay code image (0x16000 bytes -> 0x80146000; `extract_overlay.py`'s
signature sits at sectors 5970, 6205, ... 7380), +203 = 16 sectors of terrain graphics
(`func_80024E58` loads `0x1791 + 235*terrain`, 0x10). Sectors +0..+202 are identical across the 7
packages; only the tail differs. Consequence for mods: the table is rewritten from disc at the
start of every duel.

**Consuming.** `table801a7ad8_recipe_lookup` (0x8002C7E8, IDB `checkRitual`; matched C in
`src/table801a7ad8_recipe_lookup.c`):

    e = gDuel_awRitualData
    while e[0] != key: if e[0] == 0 return 0; e += 5        # key = card id of the spell played
    cand[0..4] = the caster's 5 field slots (D_801A7AD8 rows 5.. or 20.., 28-byte records, +0x16 bit 0x8000 = occupied)
    for each of e[1], e[2], e[3]: find a still-unused slot whose card id (+0xC) equals it, else return 0
    if out: out->f0/f4/f8 = the 3 matched objects, out->fC = 0
    return e[4]                                               # result card id

Callers: `func_8002622C` (player path: key = the card being played from `gp+0x2CA`; a non-zero
result goes to `gp+0x298`, spawns effect 0x12 via `func_8002C68C`, plays a sound and calls
`func_80029164(1, result)` to place the result), `obj_lifecycle_state_dispatch` (0x800262F8, calls
it again with an `out` struct to collect the three field objects), and the AI opcode
`AiScript_CheckRitual` (0x800725C4). Rules that fall out of the code:

- the three materials must be **exact card ids on the caster's own field**, any order, one slot
  each (three Blue-eyes for Ultimate Dragon); no "any Dragon" wildcards, no hand/deck materials;
- the first record whose key matches wins, so a spell can have only one recipe; the key is compared
  as a full u16, so any non-zero `type` bits make a record unmatchable;
- the list is only bounded by the zero record: the 0x800-byte slot holds up to 203 records, the
  site's 24 is a UI limit;
- the result is placed as a new monster; nothing checks that `result` is a monster or that the
  spell is type 22 — both are site-side filters.

## 3. Recomp options

1. Data hook, per frame: the table is base-EXE RAM but re-streamed per duel, so use the
   free-duel idiom — when `psx_mod_read_half(0x801799D8) == 670` and the second record reads 671
   (stock signature), overwrite records from a player file (CSV from `ritual_editor.py dump`) with
   `psx_mod_write_half`, up to 203 records + terminator. Terrain-specific recipes: key the file on
   `gDuel_bTerrain` (0x8009B364).
2. Native replacement: hook `table801a7ad8_recipe_lookup` and reimplement it over a mod-owned
   recipe list. Same inputs (key, `out`), so the three callers keep working, and the mod can add
   what the table cannot express (type wildcards, 1-2 materials, several recipes per spell).
3. Disc-level: patch WA_MRG.MRG sectors `5935 + 235k` at load if the runtime exposes CD reads;
   equivalent to what the site ships.

## 4. Decomp findings (proposed)

- `0x801799D8 gDuel_awRitualData` | 24 records of 5 u16 `[spell, mat1, mat2, mat3, result]` + zero terminator, one 0x800-byte sector copied from WA_MRG sector `5935 + 235*gDuel_bTerrain` (terrain package +105); site edits all 7 | keep name; document layout
- `0x8001798C` | requests the terrain package: `func_80014E1C(0,0, 0x16C6 + 235*gDuel_bTerrain, 0xEB, 0x800171A8, 0,0)` | `Duel_LoadTerrainPackage`
- `0x800171A8` (`select_sound_preset`) | duel package load state machine; cases set (dest,size) = (gDuel_awEquipTable,0x2800), (gDuel_aFusionTable,0x10000), (gDuel_awRitualData,0x800), plus LoadImage2 uploads | `Duel_PackageLoadStep` (rename away from sound)
- WA_MRG terrain package k (k=0..6) | sectors `5830+235k .. 6064+235k`: +105 ritual table, +140 duel overlay image (0x16000 -> 0x80146000), +203 terrain gfx (16 sectors, `func_80024E58` loads `0x1791+235k`); sectors +0..+202 identical in all 7 | evidence for the overlay LBA (5970+235k, not 0)
- `0x8002C7E8 table801a7ad8_recipe_lookup` | matches the played spell's record, consumes 3 exact field monsters, returns the result id | `Duel_FindRitualRecipe`
- `0x8002622C` | player-side ritual: lookup(0, gp+0x2CA) -> gp+0x298, effect 0x12, `func_80029164(1,result)` | `Duel_TryRitualSummon`

## 5. Open questions

- Which `gDuel_bTerrain` value is which field (0..6 order); the site writes all seven so it never
  had to know.
- Exact package sectors of the equip (0x2800) and fusion (0x10000) chunks (the state machine reads
  them, sizes known, order not confirmed on disc).
- The `type` field (bits 10-11): unused by the game's compare; the site keeps it at 0.
- Module `8481` in chunk-common also exports `jumps/buffer/script` patch data (WA 0xB97900,
  `j 0x80179B48`-style words at SLUS 118772/118960/118992) — that belongs to the "process-ritualengine"
  tool, not to this editor.
- Nothing is done server-side beyond the analytics POST.
