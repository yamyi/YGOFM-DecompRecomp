# Free Duel Theme (process tool)

Route: `extend/tools/process/freedueltheme`. Input: SLUS_014.11 only (`.11`, 1,782,579..2,097,152 bytes).
Purpose: pick the duel BGM ("theme") per Free Duel opponent. The site installs an 84-byte code
patch in the duel-setup function and a 40-byte per-opponent table in the unused tail of the EXE,
then lets you choose one of 57 tracks for each of the 39 opponents ("RESET" panel = install /
re-default, "THEMES" panel = per-opponent dropdown). Client-side only; the page POSTs analytics to
`api/v2/tools` on save, the bytes come from `chunk-common` module `1929` (offsets `i=87496`,
`r=1882128`, default `"27"`, code array `s`, theme list `e`).
Status: decoded, stock bytes verified against the real SLUS, script round-trips byte-exact, not yet
built as a recomp mod.
Script: `scripts/freeduel_theme.py` (inspect / apply / restore). Patch dump + disassembly: `patch/`.
Track list: `themes.txt` (57 entries, value 0x00..0x38). Raw notes: `NOTES-raw.md`.

## 1. The code patch: `init_800eb26c_fields_from_args` body

| | |
|---|---|
| file offset | 0x155C8, 84 bytes |
| RAM | 0x80024DC8..0x80024E1B = the whole body of `init_800eb26c_fields_from_args` (decomp, matched C in `src/init_800eb26c_fields_from_args.c`) |
| stock | `li v0,0x7270; sh v0,D_8009B36A; li v0,0x7280; sh v0,D_8009B374; li v0,3; sb a0,D_8009B360; sb a1,gDuel_bOpponentID; sh a2,D_8009B370; sh a3,D_8009B372; sb 0,gDuel_bTerrain; sb 0,D_8009B369; sb v0,D_8009B26C` |
| patched | see below; `jr ra` at 0x80024E1C is untouched |

Patched listing (`patch/code_000155c8.dis`):

    80024dc8  lui   v0,0x801e
    80024dcc  addu  v0,v0,a1            ; a1 = opponent id
    80024dd0  lb    v0,-0x4ff0(v0)      ; v0 = table[id]  (0x801DB010 + id, SIGNED byte)
    80024dd4  nop
    80024dd8  sll   v0,v0,4
    80024ddc  addiu v0,v0,0x7000        ; preset = 0x7000 + 16*theme
    80024de0  nop x4
    80024df0  lui   at,0x800a
    80024df4  sh    v0,-0x4c96(at)      ; D_8009B36A = preset          (stock: 0x7270)
    80024df8  li    v0,0x7280
    80024dfc  sh    v0,-0x4c8c(at)      ; D_8009B374 = 0x7280          (unchanged)
    80024e00  sb    a0,-0x4ca0(at)      ; D_8009B360 = a0
    80024e04  sb    a1,-0x4c9f(at)      ; gDuel_bOpponentID = a1
    80024e08  sh    a2,-0x4c90(at)      ; D_8009B370 = a2
    80024e0c  sh    a3,-0x4c8e(at)      ; D_8009B372 = a3
    80024e10  sb    zero,-0x4c9c(at)    ; gDuel_bTerrain = 0
    80024e14  sb    zero,-0x4c97(at)    ; D_8009B369 = 0
    80024e18  sb    v0,-0x4d94(at)      ; D_8009B26C = 0x80  <-- stock stored 3 (the `li v0,3` was dropped)

The stock 0x7270 = 0x7000 | (0x27 << 4): the theme numbers of the site are exactly the middle byte
of the game's sound-preset code, and 0x27 is the stock free-duel track. Consumers of D_8009B36A are
`func_8001825C` (0x8001848C) and `func_80018608` (0x800187AC), both `lhu a0,D_8009B36A; jal
call_masked_and_store_orred` = "start this preset" in the sound driver.

## 2. The data: per-opponent theme table

| | |
|---|---|
| file offset | 0x1CB810, 40 bytes |
| RAM | 0x801DB010..0x801DB037 (EXE tail, all zero in stock from 0x801D9800 to the end of the image) |
| layout | `u8 theme[40]`, index = `gDuel_bOpponentID` (1 = Simon Muran ... 39 = Duel Master K, string ids 809..847); index 0 unused (written 0) |
| default | every entry 0x27 on install ("RESET") |

The dropdown values are the 57 tracks of `themes.txt` (0x00 Main Menu ... 0x27 free duel ... 0x38
Simon Muran). Nothing clamps the byte: values above 0x38 produce presets the driver may not have.

## What the game does with it

`init_800eb26c_fields_from_args(a0, a1, a2, a3)` is called from three places:

| caller | args | effect of the patch |
|---|---|---|
| free-duel module 0x80168F84 (module base WA 0xF6D000 = in-file sector 0x1EDA, load 0x1E88+0x57) | `(-1, row*5+col, 0x6000, 0x6000)`; row/col = `gFreeDuel_bCursorRow/Column`, cell 1 = Simon | theme = table[opponent id]. Right after the call the module stores `D_8009B368 = 6` and **`D_8009B26C = 3`**, which hides the dropped `li v0,3` |
| `func_80030F40` (0x80030F68) | sets D_8009B36A = 0x71D0 then `(-1, 1, 0x8000, 0x8000)` | theme = table[1] (Simon's entry); D_8009B26C ends as 0x80 instead of 3 |
| `mask_test_800eb26c_reinit_and_poll` (0x8002DD3C) | `(-1, -1, 0, 0)` | `lb` with a1 = -1 reads 0x801DB00F (zero) -> preset 0x7000 (track 0 = main-menu music); D_8009B26C = 0x80 |

Campaign duels never pass here: the script opcode handler `func_80038530` stores gDuel_bOpponentID
itself and writes D_8009B36A / D_8009B374 from the script stream (0x80038608 / 0x80038614..0x80038660),
so their music is unchanged. D_8009B26C is the mode/state byte (`Main_RunCampaignMap` gates its
one-shot init on bit 0x40 of it; `func_800283F4` tests `(D_8009B26C & 0x1F) == 0xE`); storing 0x80
instead of 3 is a real deviation the site accepted, apparently without visible effect in free duel
because the module rewrites it.

## Recomp options

1. **Same patch, once at startup.** Base-EXE code: `psx_mod_write_code_word` the 21 words at
   0x80024DC8 and fill 0x801DB011..0x801DB037 from a player file (`opponent = track`). Better: keep
   the `li v0,3` by dropping one of the four nops (the patch has 16 spare bytes).
2. **Native replacement (cleaner).** Hook `init_800eb26c_fields_from_args` and, after it runs,
   overwrite `D_8009B36A` with `0x7000 | (theme[a1] << 4)` when `1 <= a1 <= 39`; leave the -1 paths
   alone. No RAM table needed, no state-byte side effect.
3. **Per-duelist packs.** Since the free-duel module passes the grid id, a "duelist pack" system can
   carry its own theme byte and apply it at the same hook (see the free-duel rows mod).

## Decomp findings (proposed)

- 0x8009B36A | u16 sound-preset code played at duel start; 0x7000 | track<<4; 0x7270 free duel, 0x71D0 via func_80030F40, script-driven in campaign; read by 0x8001848C / 0x800187AC | `gDuel_wBgmPreset`
- 0x8009B374 | companion u16 preset 0x7280, also script-set in func_80038530 | `gDuel_wBgmPreset2` (role unconfirmed)
- 0x80024DC8 | duel setup from args: kind(a0) / opponent(a1) / two u16 (a2,a3; 0x6000 free duel, 0x8000 func_80030F40, 0 campaign-poll path), zeroes terrain + D_8009B369, sets mode byte D_8009B26C = 3 | `Duel_SetupFromArgs`
- free-duel module | code sub-module starts at WA in-file sector 0x1EDA (0xF6D000) within the 0x1E88+0x57 load; confirm handler at module +0xF00..0xFB0 calls 0x80024DC8 with a1 = row*5+col and then sets D_8009B368 = 6, D_8009B26C = 3 (resolves F83 "file not yet identified") | `FreeDuel_ConfirmOpponent`
- 0x801D9800..0x801E0000 | zero in the stock image; TEA tools park data/code here (this tool 0x801DB010, banlist 0x801DB040/0x801DB130, old cardcolor 0x801DADE0/0x801DAE24/0x801DAF90) | reclaimed-RAM note

## Open questions

- Whether D_8009B26C = 0x80 on the two non-free-duel paths has any effect (the reader at 0x80028878 masks 0x1F so 0x80 reads as mode 0).
- The theme list names 57 presets; the driver's real preset count was not checked.
- Server side: nothing besides the analytics POST.
