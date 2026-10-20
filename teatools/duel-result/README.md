# DUEL RESULT tool

Route: `extend/tools/duel`. Input: SLUS_014.11 (accepts `.11`, 1,902,591..2,097,152 bytes).
Three independent patches, all applied client-side, file downloaded back.
Script: `scripts/duel_result.py` (inspect / apply / restore on a SLUS copy).
Raw session notes: `NOTES-raw.md`.

## 1. Bonus starchips per duel

| | |
|---|---|
| file offset | 0x126DC |
| RAM | 0x80021EDC, inside `Duel_MaybeEndOfDuel` (0x800218F0) |
| stock word | `00000000` (nop) |
| patched word | `0x2463NNNN` = `addiu v1, v1, N`, N = 0..10000 |

Context (stock):

    80021ECC  lw   v0, 0x2E0(gp)      ; duel-state object (D_8009B1E8)
    80021ED0  lw   a0, 0x2D0(gp)      ; current player's record
    80021ED4  lbu  v1, 0x3A(v0)       ; this duel's starchip prize (u8)
    80021ED8  lw   v0, 0x5E0(a0)      ; player's starchips (u32)
    80021EDC  nop                     ; <-- patch slot
    80021EE0  addu v0, v0, v1
    80021EE4  sw   v0, 0x5E0(a0)
    ...       clamp to 999,999 (0xF423F)

Game facts: player record +0x5E0 = starchips (cap 999,999); duel object +0x3A = prize; +0x3C = card drop id.

Recomp: one `psx_mod_write_code_word(0x80021EDC, 0x24630000 | n)`; base-EXE code, so apply once
at startup. A nicer mod would multiply instead of add: replace the nop with `sll v1, v1, k`
(`0x00031800 | (k << 6)`) for x2/x4 prizes.

## 2. Result-screen number colours

| | |
|---|---|
| file offset | 0x1247C (8 bytes) |
| RAM | 0x80021C7C..0x80021C80, same function |
| stock words | `00021400` `00021403` (`sll v0,v0,16` / `sra v0,v0,16`) |
| patched words | `0x2405CCYY` (`li a1, (COM<<8)\|YOU`) then `0xAC655708` (`sw a1, 0x5708(v1)`, v1 = 0x801D0000) |

The store lands on `D_801D5708`, a 16-byte **text colour-slot table**: text-stream bytes
0x80..0x8F index it (`func_80038498`), and `func_8003C4E0` seeds slots to 4 / active 0 / other 2.
Slots 0 and 1 colour the YOU / COM numbers on the result screen. Values:

    0 white  1 yellow  2 blue  3 green  4 grey  5 orange  6 red

The sign-extension that gets overwritten fed `sw v0, gDuel_CardDropID2`; the tool treats losing it as harmless.

Recomp: cleaner than the site's version: leave the code alone and write the two bytes
`D_801D5708[0]`, `[1]` from a frame hook whenever the result screen is up (or install a tiny
stub in reclaimed RAM and jump to it from 0x80021C7C, preserving the sll/sra).

## 3. Player name instead of "YOU" on the result screen

| | |
|---|---|
| file offset | 0x1A0D14 (3 bytes) |
| RAM | 0x801B0514 = `gText_aBank` + 0x514, inside text string 62 |
| stock bytes | `24 21 35` = Y O U |
| patched bytes | `FC 5A 12` = "insert player name" control sequence |

Strings 62/63 of the bank are the result labels:

    62 @0x50E: f8 17 14 05 18 05 | 24 21 35 ff | 00 3d 2f ff     "YOU"
    63 @0x51C: f8 17 22 05 26 05 | 2b 21 1e ff | 00 3a 2f ff     "COM"

`FC 5A 12` appears ~100 times across the dialogue bank; string 2 is "NAME:" + the same sequence.
Charset facts (frequency-ordered): Y=24 O=21 U=35 C=2B M=1E N=2C A=18 E=25 ':'=48, space=00, '.'=0B, FF terminator.

Recomp: data patch, three bytes at 0x801B0514, apply once (the text bank is part of the EXE image).
Same trick works for any other fixed label you want personalised.
