# Unique Drop process

Route: `extend/tools/process/uniquedrop` (V.220823, marked BETA). Inputs: SLUS_014.11
(`.11`) and WA_MRG.MRG (`.mrg`); the WA file is only touched for mods that already carry
TEA's multi-drop process. Client-side only.

Purpose: give a fixed "first-win" reward per campaign opponent. While the opponent's bit
in the free-duel unlock mask is still clear, a won duel against them always awards the
chosen card instead of a weighted roll; once the story unlocks them the normal drop
tables apply. Up to 39 opponent -> card pairs.

Status: decoded, stub disassembled, stock bytes verified, game-side flag identified
(`gFreeDuel_dwUnlockedDuelists`). Script: `scripts/unique_drop.py` (inspect / apply /
restore; restore is byte-exact).

## 1. The patch (stock single-drop SLUS)

| | file offset | RAM | stock bytes | patched bytes |
|---|---|---|---|---|
| hook | 0x12084 (8 B) | 0x80021884, epilogue of `Duel_SelectCardDrop` | `1400BF8F` `1000B08F` = `lw ra,0x14(sp)` / `lw s0,0x10(sp)` | `AC6C0708` `0A80013C` = `j 0x801DB2B0` / `lui at,0x800A` |
| stub | 0x1CBAB0 (128 B) | 0x801DB2B0 | zeros (zero run 0x801D916F..0x801E0000 in the file) | code below |
| table | 0x1CBB30 (80 B) | 0x801DB330 | zeros | u16 card id per opponent, index = opponent id 1..39 (entry 0 unused) |

The site writes the hook and stub, zeroes entries 1..39, then lets you pick a card and
tap opponent names (`setInfo` writes `cards[i].card.id` at table + 2*(i+1)); removing a
card writes 0. Loading an already-processed SLUS zeroes the table again before reading
it, so the previous mapping is not shown back.

Stub (objdump; `at` arrives as 0x800A0000 from the delay slot):

    801DB2B0  addiu at, at, -0x4C9F      ; at = 0x8009B361 = gDuel_bOpponentID
    801DB2B4  lbu   at, 0(at)            ; id (1..39)
    801DB2B8  lui   v1, 0x801D
    801DB2BC  addiu v1, v1, 0x6F4        ; gFreeDuel_dwUnlockedDuelists (0x801D06F4)
    801DB2C0  sra   s6, at, 3
    801DB2C4  addu  v1, v1, s6
    801DB2C8  lbu   v1, 0(v1)            ; byte id>>3
    801DB2CC  andi  s7, at, 7
    801DB2D0  li    s6, 7
    801DB2D4  subu  s6, s6, s7
    801DB2D8  srav  s6, v1, s6
    801DB2DC  andi  s6, s6, 1            ; bit (7 - (id & 7)), MSB first: id 1 -> 0x40
    801DB2E0  bnez  s6, 801DB310         ; already unlocked -> keep the rolled v0
    801DB2E8  lui   v1, 0x801E
    801DB2EC  addiu v1, v1, -0x4CD0      ; table 0x801DB330
    801DB2F0  sll   at, at, 1
    801DB2F4  addu  v1, v1, at
    801DB2F8  lhu   s6, 0(v1)            ; table[id]
    801DB300  beqz  s6, 801DB310         ; no unique card configured -> keep roll
    801DB30C  move  v0, s6               ; return the unique card
    801DB310  lui   at, 0x8010
    801DB314  addiu v1, v0, -1
    801DB318  move  s6, zero             ; (!) s6/s7 were used as scratch and are
    801DB31C  move  s7, zero             ;     zeroed, not restored
    801DB320  lw    ra, 0x14(sp)         ; the two displaced instructions
    801DB324  lw    s0, 0x10(sp)
    801DB328  j     0x8002188C           ; jr ra / addiu sp,sp,0x18

Multi-drop variant: if the 144-byte multi-drop signature is present at 0x801AABC0 the
hook goes to file 0x19B4D8 (RAM 0x801AACD8, `j 0x801DB2B0` / `slti at,s6,2`), the stub is
a sibling using s4/s5 that only fires for the first of the multiple drops and returns to
0x801AACE0, and the same 8-byte hook is written into WA_MRG at `0xBC1CB4+0x24 + k*0x75800`
(12328152 + k*481280, k = 0..6). Not reproduced by the script.

## 2. What the game does with it

`Duel_SelectCardDrop(tier)` (0x80021810) is called once per won duel from
`Duel_MaybeEndOfDuel` at 0x80021C60 (tier 0/1/2 from the duel rank, see
`../drop/README.md` section 3); its return value is stored to `gDuel_wSelectedCardID`,
the duel object +0x3C and `gDuel_CardDropID2`, and banked into the trunk later at
0x80021F14. Hooking the epilogue therefore overrides the card no matter which tier
was rolled, and the RNG stream is unchanged (the roll still happens).

`gFreeDuel_dwUnlockedDuelists` (0x801D06F4, save block) is the bitmask the FREE DUEL
grid is built from (decomp F64: a save with only Simon reads 0x40 = bit 6 of byte 0,
which is exactly the stub's `7 - (1 & 7)` bit for id 1). The bits are set by campaign
progression, not by the drop code, hence the site's own caveats:

- Heishin: the campaign requires losing to him first; if a mod lets you win before the
  story flips his bit, every win keeps giving the unique card.
- Duel Master K (id 39): the free-duel init never clears his cell (F84: (7,4) is
  available even on a fresh save) and no stock event sets his bit, so he always drops
  the unique card.
- One card per opponent per save; the mapping is global (campaign and free duel share
  the mask, and in free duel the opponent is by definition unlocked, so it only fires
  there for id 39).

Quirks: s6/s7 are callee-saved registers; the stub trashes them and zeroes them on the
way out instead of restoring, so any live s6/s7 up the call chain (Main_Loop's dispatch)
is corrupted - `Duel_MaybeEndOfDuel` itself does not save them, so it was not using
them. The stub/table region 0x801DB2B0..0x801DB380 is not referenced by the EXE, but it
sits between the runtime buffers `D_801DA000` and `gLibrary_aCardArtRecord` (0x801DC000),
so it could be overwritten by a load on another screen; the duel path only needs it
intact at the end of a duel.

## 3. Recomp options

1. Native, no code patch: hook `Duel_SelectCardDrop`'s return (the recomp already
   dispatches this function in `src/psx_card_drops.c`, `PSX_DROP_ROLL_SITE` = 0x80021C68).
   In the hook: `id` = the byte at 0x8009B361, `mask` = the byte at 0x801D06F4 + (id>>3),
   bit `0x80 >> (id & 7)`; if clear and `unique[id] != 0`, set `v0 = unique[id]`. Table from
   an INI/CSV in the player-data folder.
2. Nicer semantics than the site: track "unique already given" with a mod-owned flag per
   save instead of the unlock mask (fixes Heishin / Duel Master K), or key it on the
   opponent's win counter (`g_DuelSavePtrs + 0x518`, F73) == 1.
3. Byte-exact clone (not recommended): write the 8-byte hook with
   `psx_mod_write_code_word(0x80021884, 0x08076CAC)` + `(0x80021888, 0x3C01800A)` once at
   startup and the 128-byte stub + table as data at 0x801DB2B0; base-EXE bytes, so no
   per-frame re-assert is needed.

## 4. Decomp findings (proposed)

- 0x801D06F4 | bit order of `gFreeDuel_dwUnlockedDuelists` is MSB-first: opponent id -> byte id>>3, bit 0x80>>(id&7) (id 1 = 0x40, matches F64) | extent >= 5 bytes for ids up to 39
- 0x80021884 | `Duel_SelectCardDrop` epilogue is the community "unique drop" hook point; v0 override here reaches gDuel_wSelectedCardID, duel+0x3C, gDuel_CardDropID2 | (fact)
- 0x801DB2B0..0x801DB380 | zero in the EXE, not referenced by EXE code; used by the site as a code/data arena | needs a runtime-liveness check before the recomp reuses it

## 5. Open questions

- Whether anything writes 0x801DA000..0x801DC000 at runtime (library art staging?) -
  would explain the tool's BETA label.
- The multi-drop sibling stub and its WA offsets were decoded but not tested.
- Server side: only the `api/v2/tools` download log.
