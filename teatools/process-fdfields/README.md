# FREE DUEL FIELDS tool

Route: `extend/tools/process/fdfields` (login-gated). UI "V.240601", component `FreeDuelFields`,
loader = the shared `Tree` component with `to-load: ["SLUS_014.11"]`. **SLUS_014.11 is the only file
touched**, and the only file offered for download. Analytics POST `api/v2/tools` `tipo` 39 (comments
box `guia` 49). Script: `scripts/fd_fields.py` (inspect / apply / set / restore on a SLUS copy).
Patch blobs + disassembly: `patch/`. Raw notes: `NOTES-raw.md`.

Purpose: give every Free Duel opponent its own terrain instead of the stock "always terrain 0", and
switch that terrain once you have beaten the opponent enough times ("Limit" / "Start Field" /
"Final Field" in the UI).

Status: both code variants decoded and verified against the stock EXE, the win-count table the code
reads is now pinned down in the free-duel disc module (§3), `fd_fields.py` round-trips byte-for-byte.
Two shipped defects (§5). Not yet built as a recomp mod.

## 1. What it writes

| file offset | RAM | size | contents |
|---|---|---|---|
| 0x15608 **or** 0x15610 | 0x80024E08 / 0x80024E10 | 8 | `j 0x801BFE60` + `lui s1, 0x801C` (delay slot) |
| 0x1B0660 | 0x801BFE60 | 96 | 24 instructions of new code |
| 0x1B06C0 | 0x801BFEC0 | 160 | the data table: 40 x u32, index = opponent id |

Which of the two hook sites is used depends on `codeType`:

- **type 1** — stock EXE. The hook goes at 0x80024E08.
- **type 2** — an EXE that already carries the
  [Free Duel special theme](../process-freedueltheme/README.md) patch, which compacts the same
  function by 8 bytes; the hook then goes at 0x80024E10. The UI warns: *"you must apply the special
  theme first and then use the custom fields; doing it the other way around will block the necessary
  areas"*, which is exactly this — the theme patch would overwrite the fdfields jump.

Detection (`checkSlus` / `validateBytes`): `validation_type_1/2` look for `lui s1,0x801C` in the delay
slot; `validation_free_1/2` look for the untouched stock/theme byte pattern.

**Where the new code goes.** 0x801BFE60..0x801BFF5F is **zero fill inside the EXE image**: the
dialogue text bank `gText_aBank` (0x801B0000) ends at 0x801BFB4D and the next live data is the
offset table `gText_aBankOffsets` at 0x801C0000, leaving a verified **1202-byte all-zero hole,
0x801BFB4E..0x801BFFFF**. The tool's 256 bytes of code+table sit in the last quarter of it. Not PsyQ
debug strings (those are the 0x80010000..0x80012xxx block that process-cardcolor and
process-guardianstars use) and not reclaimed RAM — just padding in the loaded image. The tool also offers a "custom address" box, see §5B.

Data record, one u32 per opponent (`createDataSet` / `updateDataSetonFile`):

    bits  0-15  limit         duel-win threshold (u16)
    bits 16-19  fieldid1      terrain while wins <  limit    ("Start Field")
    bits 24-27  fieldid2      terrain while wins >= limit    ("Final Field")

Terrain names in the UI: `0 "-" 1 FOREST 2 WASTELAND 3 MOUNTAIN 4 MEADOW 5 SEA 6 DARK`.
Row 0 (the Build Deck tile) is written by `applyMinPatch`'s zero fill and never edited; the UI edits
ids 1..39 and labels them from SLUS name strings 808..847 (`Build Deck`, `Simon Muran`, `Teana`, ...,
`Nitemare`, `Duel Master K`). A freshly applied patch zeroes all 40 records, so `wins < 0` is false
everywhere and every duel uses `fieldid2 = 0` — i.e. stock behaviour.

## 2. The hook — stock bytes and what it replaces

Victim: `init_800eb26c_fields_from_args` at **0x80024DC8** (matched C in
`~/ygofm-decomp/src/init_800eb26c_fields_from_args.c`; proposed `Duel_SetDuelParams`). It is the
leaf that the free-duel screen calls to stage a duel — finding F82 records the call as
`init_800eb26c_fields_from_args(-1, row*5+col, 0x6000, 0x6000)`, so **`a1` is the opponent id**.

    void init_800eb26c_fields_from_args(a0, a1, a2, a3) {
        D_8009B36A = 29296;  D_8009B374 = 29312;
        D_8009B360 = a0;     gDuel_bOpponentID = a1;
        D_8009B370 = a2;     D_8009B372  = a3;
        gDuel_bTerrain (0x8009B364) = 0;    <-- the store the tool steals
        D_8009B369     (0x8009B369) = 0;
        D_8009B26C = 3;                      // duel start
    }

| RAM | stock bytes | stock instruction | patched bytes |
|---|---|---|---|
| 0x80024E08 (type 1) | `64 b3 20 a0` | `sb zero, %lo(gDuel_bTerrain)(at)` | `98 ff 06 08` = `j 0x801BFE60` |
| 0x80024E0C (type 1) | `0a 80 01 3c` | `lui at, %hi(D_8009B369)` | `1c 80 11 3c` = `lui s1, 0x801C` |
| 0x80024E10 (type 2) | `64 b3 20 a0` | (same store, moved down 8 bytes by the theme patch) | `98 ff 06 08` |
| 0x80024E14 (type 2) | `69 b3 20 a0` | `sb zero, %lo(D_8009B369)(at)` | `1c 80 11 3c` |

Note the delay slot: the tool does not preserve the instruction it displaces, it *replaces* it with
the `lui s1, 0x801C` the new code needs, and lets the injected code re-do the store. In type 1 the
displaced instruction is a redundant `lui at, 0x800A` (at already holds 0x800A0000 from 0x80024E04),
so nothing is lost; in type 2 the displaced instruction is the real `sb zero, D_8009B369`, which is
why the injected code carries its own copy (`sb zero, 0xB369(at)` at 0x801BFE74).

## 3. The injected code (`patch/mainScript_type1_801BFE60.dis`)

    801BFE60  addiu s1, s1, -320        ; s1 = 0x801C0000 - 0x140 = 0x801BFEC0 (the table)
    801BFE64  sll   s2, a1, 2           ; a1 = opponent id
    801BFE68  addu  s1, s1, s2          ; -> our record
    801BFE6C  lui   s4, 0x801D
    801BFE70  lhu   s3, 0(s1)           ; limit
    801BFE74  sb    zero, 0xB369(at)    ; D_8009B369 = 0   (at is still 0x800A0000)
    801BFE78  addiu s4, s4, 0x71C
    801BFE7C  addu  s4, s4, s2          ; -> gFreeDuel_aDuelistRecords[id]
    801BFE80  lhu   s5, 0(s4)           ; wins against this duelist
    801BFE88  slt   s2, s5, s3          ; wins < limit ?
    801BFE90  lbu   s3, 2(s1)           ; fieldid1
    801BFE98  bnez  s2, 801BFEA8
    801BFE9C   move s5, zero
    801BFEA0  lbu   s3, 3(s1)           ; fieldid2
    801BFEA8  sb    s3, 0xB364(at)      ; gDuel_bTerrain = chosen field
    801BFEAC  move  s1, zero
    801BFEB0  move  s2, zero
    801BFEB4  move  s3, zero
    801BFEB8  j     0x80024E10          ; (type 2: 0x80024E18) -- back into the stock tail
    801BFEBC   move s4, zero

The counter it reads, `0x801D071C + 4*id`, was previously unidentified in the decomp (findings F25 /
F73 call the per-duelist increment site "still unlocated"). It is resolved here: the array is
**40 records of {u16 wins, u16 losses}** and both the reader and the writer live in the free-duel disc
module, not in the EXE, which is why nothing in `asm/` references the address. Evidence in
WA_MRG.MRG (the free-duel screen package, sectors 0x1E88..0x1EDE):

- in-file **0xF6D15C** (`FreeDuel_PlaceCursor`, 0x80168090, finding F80): after checking
  `gFreeDuel_abGridAvailable` (0x80169030), it does
  `lh a0, 0x71C(0x801D0000 + 4*(row*5+col))` -> `D_801D5608`, `lh v1, 0x71E(...)` -> `D_801D560C`,
  i.e. the W/L pair shown next to the selected duelist;
- in-file **0xF6D2A8** (post-duel bookkeeping): `v1 = (row*5+col) << 2`,
  `a0 = 0x801D071C + v1`, `if (D_8009B362 == 1) a0 += 2` (loss instead of win), then
  `*(u16*)a0 += 1` clamped to **999**.

The array runs 0x801D071C..0x801D07BB, ending exactly where `gDuel_awRecentCardDrops` (0x801D07BC)
begins, and the index is the same `row*5+col` the hook receives in `a1`. So the tool's "Limit" really
is *wins*, not duels played.

## 4. Where the terrain goes afterwards

`gDuel_bTerrain` (0x8009B364) is the byte the duel loader reads: `func_8001798C` issues
`func_80014E1C(0, 0, 0x16C6 + 235*gDuel_bTerrain, 0xEB, 0x800171A8, 0, 0)`, i.e. it picks one of the
seven 235-sector "terrain packages" (see [data-ritualeditor](../data-ritualeditor/README.md) §2), and
`func_80024E58` loads the matching 16 sectors of terrain graphics (`0x1791 + 235*terrain`). So this
one byte selects the field art, the field-power rules and the copy of the ritual/equip/fusion tables
used for the whole duel. Campaign duels set it elsewhere; only the free-duel path is hooked here.

## 5. Defects in the shipped tool

**A. The type-2 body has a hole in it.** The JS array for `mainScript_2` is written

    [...,134,147,0,8,,33,160,0,0]
                     ^ a real JavaScript array HOLE at index 92

`Array.prototype.forEach` skips holes, so byte 92 is never written and the last four bytes land one
position late. The delay slot of the final `j` — meant to be `move s4, zero` (`00 00 a0 21` LE
`0x0000A021`) — comes out as `0x00A02100`, which is an `SLL` with a non-zero `rs` field: objdump
refuses it as a reserved encoding, and the R3000 executes it as `sll a0, zero, 4`, i.e. it zeroes
**a0** and leaves `s4` holding `0x801D071C + 4*id`. `a0` has already been consumed at that point
(0x80024E00 stores it), so the visible damage is only the stray `s4`; see B for why that still
matters. `patch/mainScript_type2_801BFE60_asShipped.bin` is the literal shipped result;
`..._fixed.bin` is the 24 correct words, which is what `fd_fields.py` writes by default
(`--site-bug` reproduces the shipped bytes).

**B. The code clobbers callee-saved registers.** `s1`-`s5` are all written and then zeroed rather than
saved and restored. `init_800eb26c_fields_from_args` is a leaf with no stack frame, so under the o32
ABI its caller (the free-duel module's confirm path, F82) is entitled to keep live values in `s1`-`s5`.
The zeroing is the author's mitigation, and the type-2 variant does not even manage that for `s4`.
A recomp port should use `at`/`v0`/`v1`/`t*` only, or spill to a scratch word.

**C. "Use a custom address" moves the code but not the table.** `applyMinPatch` rewrites the `j`
target and writes the 96 bytes at the custom offset, but the *table* is reached by the hard-wired
`lui s1,0x801C` / `addiu s1,s1,-320` pair, which still points at 0x801BFEC0 while the tool now edits
`customAddress + 96`. `fd_fields.py --code-addr` rewrites the `addiu` displacement as well (valid for
any address within +/-32 KB of 0x801C0000).

Minor: `bytes.bonusData` in the component is a copy-paste of the guardianstars table and is never used.

## 6. Recomp options

1. **Native replacement.** Hook `init_800eb26c_fields_from_args` (0x80024DC8) and set
   `gDuel_bTerrain` from a mod-owned per-opponent table before tail-calling the stock body. Base-EXE
   code, so `PSX_MOD_CONSTRUCTOR` + one-shot patch; no frame hook. This also sidesteps defects A-C.
2. **Byte-for-byte port.** Two `psx_mod_write_code_word` for the hook + 24 for the body + 40 for the
   table. Must decide at startup whether the freedueltheme patch is present (`psx_mod_read_word`
   at 0x80024E08 == `0xA426B370`) and pick the type-2 offsets — or, in a recomp, just implement both
   features natively and drop the interaction entirely.
3. **Richer switching.** The stock counter is `{u16 wins, u16 losses}` per duelist, so a recomp mod
   can key the terrain on losses, on wins+losses, on `gCampaign_abStoryFlags` (0x801D0618) or on a
   random roll per duel — the table format is the tool's, not the game's.
4. **Terrain per duel, not per opponent.** Since `gDuel_bTerrain` also picks which of the 7 copies of
   the ritual/equip/fusion tables is loaded, combining this with
   [process-ritualengine](../process-ritualengine/README.md) gives per-opponent *rules*, not just
   per-opponent scenery. Nothing in the game prevents it; the site's tools just never write the
   7 copies differently.

## 7. Decomp findings (proposed)

- `0x801D071C` (160 bytes) | **the per-duelist free-duel record array**: 40 x `{u16 wins, u16 losses}`, index `row*5+col` (0 = the Build Deck tile). Written only by the free-duel disc module: increment at WA in-file 0xF6D2A8 (`+2` for a loss, selected by `D_8009B362`, clamped to 999), read at WA in-file 0xF6D15C into `D_801D5608`/`D_801D560C` for the W/L display. Array ends at `gDuel_awRecentCardDrops` 0x801D07BC. Resolves the "per-duelist increment site still unlocated" note in F25/F73 | `gFreeDuel_aDuelistRecords`
- `0x8009B362` | free-duel result selector: 0 = the duel was won, 1 = lost; chooses which half of the duelist record is bumped | `gFreeDuel_bLastResult`
- `0x80024DC8 init_800eb26c_fields_from_args` | the free-duel "stage a duel" setter; `a1` = opponent id (`row*5+col`), and its `gDuel_bTerrain = 0` store is what the tool replaces to make the terrain opponent-dependent | `Duel_SetDuelParams`
- `0x801BFB4E..0x801BFFFF` (1202 bytes) | all-zero padding between the end of `gText_aBank` (last non-zero byte 0x801BFB4D) and `gText_aBankOffsets` (0x801C0000); this tool parks 256 bytes of code+table at 0x801BFE60 | free-space note
- opponent name strings | SLUS name-table entries 808..847 = `Build Deck` + the 39 duelists in grid order, ending `Duel Master K`; decoded via the name pointer table at file 0x1C5C00 (u16 offsets biased by 0x5800) | evidence for the free-duel grid order

## 8. Open questions

- The load address of the free-duel module was not pinned down here; the two evidence sites are given
  as WA_MRG in-file offsets (sectors 0x1EDA/0x1EDB of the 0x1E88+0x57 package) and their absolute
  `jal` targets confirm they run in the 0x8xxxxxxx module window.
- `D_8009B369`, cleared next to `gDuel_bTerrain` and re-cleared by the injected code, is still
  unidentified (a second terrain/theme byte is the obvious guess since the freedueltheme tool also
  works in this function).
- Whether the game clamps terrain ids above 6: the tool's nibbles allow 0..15 and the loader would
  index sector `0x16C6 + 235*terrain` straight off the end of the packages.
- Nothing is done server-side beyond the analytics POST; the route is login-gated.
