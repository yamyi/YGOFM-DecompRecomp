# RITUAL ENGINE tool

Route: `extend/tools/process/ritualengine` (login-gated). UI "Ritual Engine Editor | V. 20251123",
component `RitualConstructor`. Inputs: **SLUS_014.11** and **WA_MRG.MRG**, both loaded through the
shared `Tree` component (`to-load: ["SLUS_014.11","WA_MRG.MRG"]`) and both downloaded back.
Analytics POST `api/v2/tools` with `tipo` 44 (comments box `guia` 54); nothing else is server-side.
Scripts: `scripts/ritual_engine.py` (inspect / dump / apply / restore, SLUS and WA separately, works
on a MODE2/2352 disc image too). Patch blobs + disassembly: `patch/`. Raw notes: `NOTES-raw.md`.

Purpose: keep the ritual recipe table of the plain [Ritual Editor](../data-ritualeditor/README.md)
but give each record a **type** so a recipe can ask for a card *type* or *attribute* or "any monster"
instead of three exact card ids. That needs new code, so the tool patches the EXE as well.

Status: all three SLUS hooks and the 560-byte WA script decoded instruction by instruction and
verified against the stock US files; `ritual_engine.py` round-trips both files byte-for-byte. Two
defects found in the shipped code (see §5). Not yet built as a recomp mod.

## 1. What it writes

| file | offset | size | contents |
|---|---|---|---|
| SLUS_014.11 | 0x1CFF4 | 8 | `j 0x80179B48` + `nop` (RAM 0x8002C7F4) |
| SLUS_014.11 | 0x1D0B0 | 8 | `j 0x80179BE8` + `nop` (RAM 0x8002C8B0) |
| SLUS_014.11 | 0x1D0D0 | 8 | `j 0x80179B48` + `addiu t4,t4,10` (RAM 0x8002C8D0) |
| WA_MRG.MRG | 0xB97800 + 0x75800*k | 250 | 24 recipe records + zero terminator (RAM 0x801799D8) |
| WA_MRG.MRG | 0xB97900 + 0x75800*k | 112 | zeroed scratch block (RAM 0x80179AD8) |
| WA_MRG.MRG | 0xB97970 + 0x75800*k | 560 | the new MIPS routine (RAM 0x80179B48) |

k = 0..6, one per terrain package (`multiSetWord` / `multiSetByte`, stride 481280 = 235 sectors);
in-file sector `5935 + 235k`, disc LBA `16037 + 235k`.

**Where the new code lives.** *Not* in reclaimed EXE space and *not* on PsyQ debug strings: the game
copies a whole 0x800-byte disc sector into `gDuel_awRitualData` (0x801799D8) at the start of every
duel, and only the first 250 bytes are records. Bytes +0x100..+0x7FF are `0xFF` filler on the stock
disc (verified in all 7 copies), so the tool parks 112 bytes of scratch at +0x100 and 560 bytes of
code at +0x170. Everything still fits inside the sector (+0x3A0 is the end of the code; the buffer
runs to +0x7FF, and 0x801799D8+0x800 = `gDuel_awEquipTable`). Consequence: the code is re-streamed
from disc at every duel start, exactly like the table — nothing has to keep it resident.

Cost: because the scratch block sits at +0x100, the recipe list is hard-capped at **24 records**
(the plain Ritual Editor can use the whole sector, 203 records).

Record layout (unchanged from the Ritual Editor except the top two bits of word 0):

    u16 (type << 10) | spell_id     u16 req1   u16 req2   u16 req3   u16 result

    type 0  "Normal Ritual"           req = exact card ids (stock behaviour)
    type 1  "Ritual By Card Type"     req = card type 0..23, and material ATK < result ATK
    type 2  "Ritual By Card Attribute" req = attribute 0..7, and material ATK < result ATK
    type 3  "Ritual By any monster card" reqs ignored, material ATK < result ATK

Site UI: the type picker disables the three material pickers for types > 2; the material picker is
the card list for type 0, the 24 type names (SLUS name strings 768..791) for type 1 and the attribute
list `Light Dark Earth Water Fire Wind Magic Trap` for type 2. "Add New Combination" inserts
`type 0, spell 695, 1/1/1 -> 380`. Only 24 slots exist and the save always writes all 24 (unused ones
zeroed) plus a zero record at +240.

## 2. The three hooks — stock bytes and what they replace

The victim is `table801a7ad8_recipe_lookup` at **0x8002C7E8** (IDB `checkRitual`, proposed
`Duel_FindRitualRecipe`; matched C in `~/ygofm-decomp/src/table801a7ad8_recipe_lookup.c`).
Stock bytes verified against `~/ygofm-decomp/SLUS_014.11`.

| RAM | stock | patched | stock instruction lost |
|---|---|---|---|
| 0x8002C7F4 | `00 00 82 95` `00 00 00 00` | `d2 e6 05 08` `00 00 00 00` | `lhu v0, 0(t4)` (+ the `nop` after it) |
| 0x8002C8B0 | `00 00 22 95` `00 00 00 00` | `fa e6 05 08` `00 00 00 00` | `lhu v0, 0(t1)` (+ `nop`) |
| 0x8002C8D0 | `4c b2 00 08` `21 10 00 00` | `d2 e6 05 08` `0a 00 8c 25` | `j .L8002C930` / `move v0, zero` (the "return 0") |

Stock control flow, with the three sites marked:

    8002C7E8  addiu sp,sp,-0x28
    8002C7EC  lui  v0, %hi(gDuel_awRitualData)
    8002C7F0  addiu t4, v0, %lo(gDuel_awRitualData)      ; t4 = record pointer
    8002C7F4  lhu  v0, 0(t4)                <-- HOOK 1   ; key of this record
    8002C7FC  beqz v0, .L8002C8D0                        ; end of table -> return 0
    8002C804  beq  v0, a1, .L8002C814                    ; a1 = the spell card played
    8002C80C  j    .L8002C7F4 ; addiu t4,t4,0xA          ; next record
    8002C814  ... collect the 5 field slots of the playing side into sp+0x10..
    8002C87C  addiu t4, t4, 0x2                          ; t4 -> req1
    8002C890  for k in 0..2: for i in 0..4:
    8002C8AC    lh  v1, 0xC(a1)                          ; candidate slot's card id
    8002C8B0    lhu v0, 0(t1)                <-- HOOK 2  ; the requirement
    8002C8B8    beq v1, v0, .L8002C8D8                   ; hit: consume the slot
    8002C8C8    ... else next candidate
    8002C8D0  j .L8002C930 ; move v0, zero  <-- HOOK 3   ; no candidate matched -> return 0
    8002C8D8  ... store the match, t1 += 2, k++
    8002C8F4  if (out) copy the 3 matched objects into out
    8002C92C  lhu v0, 0x6(t4)                            ; = record[4], the result card id

## 3. The injected routine (`patch/script_80179B48.dis`)

Scratch block `0x80179AD8`: +0x00..0x0F saved s2..s5, +0x50 the searched key (written, never read),
+0x54 the current record's spell id, +0x58 its type, +0x5C the **result card's ATK**.

### Entry A — 0x80179B48 (key compare, replaces HOOK 1 and is re-entered by HOOK 3)

    save s2..s5 to 0x80179AD8
    s2 = *(u16*)t4                       ; record word 0
    s3 = s2 & 0x3FF                      ; spell id
    s4 = (s2 >> 10) & 3                  ; ritual type
    scratch[0x50]=a1 ; [0x54]=s3 ; [0x58]=s4
    s5 = *(u16*)(t4+8)                   ; result card id
    s2 = gCard_adwStats[s5-1] & 0x1FF    ; lw at 0x801D4240 + 4*s5 -> ATK/10
    scratch[0x5C] = s2
    restore s2..s5
    v0 = scratch[0x54] & 0x3FF
    if (v0 == 0) j 0x8002C930 with v0 = 0        ; terminator -> return 0
    else         j 0x8002C804 with v0 = spell id ; resume the stock compare

The whole point of entry A is that the stock `beq v0, a1` compares a **full u16**, so any non-zero
type bits would make a record unmatchable. Masking with 0x3FF restores matching and frees bits 10-11.
As a side effect the end-of-table test moves from "word == 0" to "spell id == 0".

### Entry B — 0x80179BE8 (material compare, replaces HOOK 2)

On entry `v1` = the candidate field slot's card id (`lh 0xC(a1)`), `t1` -> the requirement u16.

    save s2..s5
    s2 = scratch[0x58] & 3               ; ritual type
    s3 = *(u16*)t1                       ; the requirement
    if (s2 != 0) goto TYPE1_3
    ;; ---- type 0: unchanged, exact card id ----
    0x80179C18: restore s2,s4,s5
                if (v1 == s3) j 0x8002C8D8   ; hit
                else          j 0x8002C8C0   ; miss (s3 restored in the delay slot)

    TYPE1_3:
      type 1: s5 = gCard_adwStats[v1-1]
              v1 = (s5 >> 26) & 0x3F                ; card TYPE
              if ((s5 & 0x1FF) >= scratch[0x5C]) { v1 = 1; s3 = 0; }   ; ATK too high -> force miss
              goto 0x80179C18
      type 2: s5 = gCard_adwStats[v1-1]
              if ((s5 & 0x1FF) <  scratch[0x5C]) v1 = gCard_abLevelAttr[v1] >> 4   ; ATTRIBUTE
              goto 0x80179C18                                                       ; (see bug B)
      type 3: s5 = gCard_adwStats[v1-1] & 0x1FF          ; candidate ATK, read first
              v1 = s3                                    ; then force a match ...
              if (s5 >= scratch[0x5C]) { v1 = 1; s3 = 0; }  ; ... unless the ATK gate fails
              goto 0x80179C18

`gCard_adwStats` = `gDuel_adwCardStats` 0x801D4244 (SLUS 0x1C4A44), one u32 per card, indexed
`base 0x801D4240 + 4*id`: bits 0-8 ATK/10, 9-17 DEF/10, 18-21 guardian star 2, 22-25 guardian star 1,
26-31 card type. `gCard_abLevelAttr` = `gDuel_abCardLevelAttr` 0x801D5332, one u8 per card (indexed by
id, entry 0 is a pad byte): high nibble = attribute 0..7, low nibble = level.

### Entry via HOOK 3 — the "another recipe for the same spell" retry

Stock `.L8002C8D0` was `return 0` when one of the three requirements found no field monster. Patched
it becomes `t4 += 10; goto entry A`, i.e. keep scanning for a *further* record with the same key —
this is what lets a spell carry a specific recipe plus a wildcard fallback. Note that HOOK 1 makes
the other predecessor of `.L8002C8D0` (`beqz v0, .L8002C8D0` at 0x8002C7FC) unreachable, so the retry
is the only way in.

## 4. What the game does with the result

Unchanged from the Ritual Editor writeup: the three callers are `func_8002622C` (player plays the
spell; a non-zero result spawns effect 0x12 and calls `func_80029164(1, result)`),
`obj_lifecycle_state_dispatch` (0x800262F8, second call with an `out` struct to collect the three
consumed field objects) and the AI opcode `AiScript_CheckRitual` (0x800725C4). Materials must still be
three **separate occupied slots on the caster's own field**, matched in order, each consumed once;
nothing checks that the result is a monster or that the spell is a Ritual card.

## 5. Defects in the shipped code

**A. The retry is off by two.** At `.L8002C8D0` the stock code has already executed
`addiu t4, t4, 0x2` (0x8002C87C), so `t4` points at *record + 2*, not at the record start. Adding 10
lands on **next record + 2**, i.e. the scan continues reading `req1` fields as record keys; the
correct constant is 8. In practice the mis-aligned scan almost always walks into the zero terminator
and returns 0 (= stock behaviour), but a `req1` value that happens to equal the played spell's id
would fire a bogus recipe. Fix for a re-implementation: `addiu t4, t4, 8`.

**B. Type 2 leaves `v1` shifted when the ATK gate fails.** In the type-2 path `v1` is scaled by
`sll v1, v1, 2` to index the stats table and only un-scaled (`srl v1, v1, 2`) on the ATK-passes
branch. When the candidate's ATK is not lower than the result's, control jumps to 0x80179D10 with
`v1 = 4 * card_id` and that value is compared against the attribute requirement. It rejects as
intended for every card except **id 1 (Blue-Eyes White Dragon), whose 4*1 = 4 collides with attribute
4 = Fire**: a Fire-attribute type-2 requirement will accept a Blue-Eyes of any ATK. The two
instructions at 0x80179D08/0x80179D0C (`li v1,1` / `li s3,1`) are dead code — they sit after the
delay slot of an unconditional `j` and can never execute.

Minor: the store of `a1` into scratch+0x50 is never read; entry A recomputes the result card's ATK
for every record it walks past, not just the matching one.

## 6. Recomp options

1. **Native replacement (recommended).** Hook `table801a7ad8_recipe_lookup` (0x8002C7E8) and
   reimplement it over a mod-owned recipe list. Same signature `(out, key)` so the three callers keep
   working, and neither of the two defects above needs porting. You also drop the 24-record cap and
   the "materials live in the ritual sector" constraint entirely, and can express things the site's
   encoding cannot (1 or 2 materials, level/star requirements, several recipes per spell without the
   retry hack).
2. **Byte-for-byte port.** The three SLUS words are base-EXE code: one `PSX_MOD_CONSTRUCTOR` +
   three `psx_mod_write_code_word` at startup. The WA side is *not* EXE bytes — it is re-streamed
   from disc per duel — so it needs the free-duel-rows idiom: a frame hook that checks
   `psx_mod_read_word(0x80179B48) != 0x3C028018` and, when the sector is resident
   (`psx_mod_read_half(0x801799D8) != 0`), writes the 140 code words plus the records with
   `psx_mod_write_code_word` / `psx_mod_write_half`. Cheaper: keep the stock lookup, install only the
   records, and hook the compare.
3. **Per-terrain recipes.** The site writes all 7 copies identically because the UI has no terrain
   selector, but the sector is chosen by `gDuel_bTerrain` (0x8009B364), so a recomp mod gets
   terrain-specific ritual rules for free by keying its record file on that byte.
4. **Disc-level.** Patch WA_MRG sectors `5935 + 235k` if the runtime exposes CD reads — exactly what
   the site ships.

## 7. Decomp findings (proposed)

- `0x8002C7E8 table801a7ad8_recipe_lookup` | the three site hook points (0x8002C7F4 key load, 0x8002C8B0 requirement load, 0x8002C8D0 return-0) pin the function's role; `beq v0,a1` compares the record key as a full u16 so bits 10-15 of word 0 are unusable in stock | `Duel_FindRitualRecipe`
- `0x801799D8 gDuel_awRitualData` | 0x800 bytes copied from disc per duel; only +0x000..+0x0F9 are records in stock, +0x0FA..+0x7FF is 0xFF filler — free space inside a per-duel streamed buffer | document the free tail
- `0x801D4244 gDuel_adwCardStats` | u32 per card (id-1): bits 0-8 ATK/10, 9-17 DEF/10, 18-21 guardian star 2, 22-25 guardian star 1, 26-31 card type. The site reads it as base `0x801D4240 + 4*id`. Stock `func_8002BFCC` and `init_container_entry_objs` mask the type with 0x1F, i.e. they only see 5 of the 6 bits | `gCard_adwStats`, document the bitfield
- `0x801D5332 D_801D5332` (already `gDuel_abCardLevelAttr` in the asm) | u8 per card indexed by **card id** (byte 0 is a pad): high nibble attribute (0 Light, 1 Dark, 2 Earth, 3 Water, 4 Fire, 5 Wind, 6 Magic, 7 Trap), low nibble level. Verified for ids 1-6 against the printed card data | `gCard_abAttributeLevel`
- card type ids | 0..19 monster families, 20 Magic, 21 Trap, 22 Ritual, 23 Equip; names are SLUS text strings 768..791 | evidence for the type enum

## 8. Open questions

- Nothing is done server-side beyond the analytics POST, but the route is login-gated, so the page
  itself is only reachable with a session cookie.
- The site never surfaces the 7 terrain copies; whether the game would accept different recipe lists
  per terrain is untested on hardware.
- Whether defect A was ever noticed by users — with the stock 24 records the mis-aligned scan is
  harmless, so a "multiple recipes per spell" setup is the only way to hit it.
